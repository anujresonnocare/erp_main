# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class CrmLead(models.Model):
    _inherit = "crm.lead"
    _ROUND_ROBIN_PARAM = "resonnocare_crm.last_assigned_user_id"

    quotation_count = fields.Integer(
        string="Quotations",
        default=0,
        help="Fallback field when sales quotation integration is not installed.",
    )
    sale_amount_total = fields.Monetary(
        string="Sales Total",
        currency_field="company_currency",
        default=0.0,
        help="Fallback field when sales quotation integration is not installed.",
    )
    sale_order_count = fields.Integer(
        string="Sales Orders",
        default=0,
        help="Fallback field when sales quotation integration is not installed.",
    )

    # ============================================================
    # STAGE 1 — LEAD CREATION (CRM OWNED)
    # ============================================================

    x_phone = fields.Char(
        string="Lead Phone",
        required=True,
        help="Primary phone number used to contact the lead.",
    )

    x_lead_source = fields.Selection(
        [
            ("call", "Call"),
            ("whatsapp", "WhatsApp"),
            ("walkin", "Walk-in"),
            ("referral", "Referral"),
            ("other", "Other"),
        ],
        string="Lead Source",
        help="Source through which the lead originated.",
    )

    x_interested_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Interested Clinic",
        help="Clinic the lead is interested in visiting.",
    )

    # ============================================================
    # STAGE 3 — CALL DISPOSITION (MASTER DRIVEN)
    # ============================================================

    x_disposition_id = fields.Many2one(
        "resonnocare.crm.disposition",
        string="Call Disposition",
        domain=[("active", "=", True)],
        help="Outcome of the latest call with the lead.",
    )

    x_attempt_count = fields.Integer(
        string="Attempt Count",
        default=0,
        readonly=True,
        help="Number of follow-up attempts made for this lead.",
    )

    x_lead_relevant = fields.Boolean(
        string="Lead Relevant",
        compute="_compute_disposition_logic",
        store=True,
        help="Computed flag indicating whether the lead is relevant.",
    )

    x_next_followup_date = fields.Date(
        string="Next Follow-up Date",
        compute="_compute_disposition_logic",
        store=True,
        help="Next follow-up date calculated from disposition rules.",
    )

    # ============================================================
    # STAGE 5 — VISIT INTENT (CRM → FRONT DESK HANDOFF)
    # ============================================================

    x_visit_intent = fields.Boolean(
        string="Visit Intent",
        default=False,
        help="Indicates whether the lead has agreed to visit a clinic.",
    )

    x_preferred_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Preferred Clinic",
        help="Clinic the lead prefers to visit.",
    )

    x_preferred_visit_date = fields.Date(
        string="Preferred Visit Date",
        help="Tentative visit date provided by the lead.",
    )

    x_preferred_appointment_type_id = fields.Many2one(
        "resonnocare.appointment.type",
        string="Preferred Appointment Type",
        domain=[("active", "=", True)],
        help="Type of appointment the lead is interested in.",
    )
    x_can_capture_visit_intent = fields.Boolean(
        string="Can Capture Visit Intent",
        compute="_compute_visit_intent_allowed",
        help="Technical flag to prevent visit intent on non-relevant or immediately churned leads.",
    )
    x_patient_id = fields.Many2one(
        "res.partner",
        string="Converted Patient",
        readonly=True,
        copy=False,
    )
    x_converted_to_patient = fields.Boolean(
        string="Converted to Patient",
        readonly=True,
        copy=False,
    )
    x_conversion_datetime = fields.Datetime(
        string="Conversion Datetime",
        readonly=True,
        copy=False,
    )
    x_call_log_ids = fields.One2many(
        "resonnocare.crm.call.log",
        "lead_id",
        string="Call Logs",
        readonly=True,
    )
    x_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Booked Appointment",
        readonly=True,
        copy=False,
    )
    x_appointment_booking_datetime = fields.Datetime(
        string="Appointment Booked On",
        readonly=True,
        copy=False,
    )

    @staticmethod
    def _normalize_phone_digits(number):
        return "".join(ch for ch in (number or "") if ch.isdigit())

    @classmethod
    def _is_valid_indian_mobile(cls, number):
        digits = cls._normalize_phone_digits(number)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return len(digits) == 10 and digits[0] in "6789"

    @api.constrains("x_phone", "phone", "mobile")
    def _check_lead_phone_numbers(self):
        for lead in self:
            for field_name, field_label in [
                ("x_phone", "Lead Phone"),
                ("phone", "Phone"),
                ("mobile", "Mobile"),
            ]:
                value = lead[field_name]
                if value and not self._is_valid_indian_mobile(value):
                    raise ValidationError(
                        _("%s must be a valid 10-digit Indian mobile number.")
                        % field_label
                    )

    # ============================================================
    # STAGE 2 — LEAD ALLOCATION (ROUND ROBIN)
    # ============================================================

    @api.model
    def _get_round_robin_crm_users(self):
        crm_group = self.env.ref("resonnocare_base.group_crm", raise_if_not_found=False)
        if not crm_group:
            return self.env["res.users"]

        return self.env["res.users"].sudo().search(
            [
                ("active", "=", True),
                ("share", "=", False),
                ("groups_id", "in", [crm_group.id]),
            ],
            order="id",
        )

    @api.model
    def _get_round_robin_assignment_ids(self, count):
        users = self._get_round_robin_crm_users()
        if not users or count <= 0:
            return []

        params = self.env["ir.config_parameter"].sudo()
        last_user_id = int(params.get_param(self._ROUND_ROBIN_PARAM, default="0") or 0)
        user_ids = users.ids

        start_index = 0
        if last_user_id in user_ids:
            start_index = (user_ids.index(last_user_id) + 1) % len(user_ids)

        assigned_ids = []
        for offset in range(count):
            assigned_ids.append(user_ids[(start_index + offset) % len(user_ids)])

        params.set_param(self._ROUND_ROBIN_PARAM, str(assigned_ids[-1]))
        return assigned_ids

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        initial_dispositions = []
        for vals in vals_list:
            vals.setdefault("type", "lead")
            if not vals.get("name"):
                vals["name"] = self._build_resonnocare_lead_name(vals)
            initial_dispositions.append(vals.get("x_disposition_id"))
        to_assign_indexes = [idx for idx, vals in enumerate(vals_list) if not vals.get("user_id")]
        assigned_user_ids = self._get_round_robin_assignment_ids(len(to_assign_indexes))

        for idx, user_id in zip(to_assign_indexes, assigned_user_ids):
            vals_list[idx]["user_id"] = user_id

        leads = super().create(vals_list)

        for lead in leads:
            if lead.user_id and lead.create_uid != lead.user_id:
                lead.message_post(
                    body=_("Lead auto-assigned to %(user)s through round robin.")
                    % {"user": lead.user_id.name}
                )

        for lead, disposition_id in zip(leads, initial_dispositions):
            if not disposition_id:
                continue
            disposition = lead.x_disposition_id
            if not disposition:
                continue

            lead.x_attempt_count += 1
            lead.env["resonnocare.crm.call.log"].sudo().create(
                {
                    "lead_id": lead.id,
                    "user_id": lead.user_id.id or self.env.user.id,
                    "disposition_id": disposition.id,
                    "attempt_number": lead.x_attempt_count,
                    "lead_relevant": lead.x_lead_relevant,
                    "next_followup_date": lead.x_next_followup_date,
                }
            )

            if disposition.lead_relevant and disposition.follow_up_days > 0:
                lead._schedule_followup_activity(disposition)

            if (
                not disposition.lead_relevant
                and disposition.max_attempts > 0
                and lead.x_attempt_count >= disposition.max_attempts
            ):
                lead._move_to_churned()

        return leads

    @api.model
    def _build_resonnocare_lead_name(self, vals):
        phone = (vals.get("x_phone") or vals.get("phone") or "").strip()
        contact = (vals.get("contact_name") or "").strip()
        source = vals.get("x_lead_source")
        source_label = dict(self._fields["x_lead_source"].selection).get(source, "")

        parts = [part for part in [contact, phone, source_label] if part]
        return " / ".join(parts) if parts else _("New Lead")

    @api.onchange("x_phone", "contact_name", "x_lead_source")
    def _onchange_resonnocare_lead_name(self):
        for lead in self:
            lead.name = lead._build_resonnocare_lead_name(
                {
                    "x_phone": lead.x_phone,
                    "phone": lead.phone,
                    "contact_name": lead.contact_name,
                    "x_lead_source": lead.x_lead_source,
                }
            )

    # ============================================================
    # COMPUTED LOGIC — DISPOSITION RULE ENGINE
    # ============================================================

    def web_save(self, vals, specification: dict[str, dict], next_id=None):
        vals = dict(vals)
        if not vals.get("name"):
            vals["name"] = self._build_resonnocare_lead_name(
                {
                    "x_phone": vals.get("x_phone"),
                    "phone": vals.get("phone"),
                    "contact_name": vals.get("contact_name"),
                    "x_lead_source": vals.get("x_lead_source"),
                }
            )
        return super().web_save(vals, specification, next_id=next_id)

    @api.depends("x_disposition_id")
    def _compute_disposition_logic(self):
        """
        Computes:
        - lead relevance
        - next follow-up date

        Entirely driven by master disposition configuration.
        """
        today = fields.Date.today()

        for lead in self:
            disposition = lead.x_disposition_id

            if not disposition:
                lead.x_lead_relevant = True
                lead.x_next_followup_date = False
                continue

            lead.x_lead_relevant = disposition.lead_relevant

            if disposition.follow_up_days > 0:
                lead.x_next_followup_date = today + timedelta(
                    days=disposition.follow_up_days
                )
            else:
                lead.x_next_followup_date = False

    @api.depends("x_disposition_id", "x_lead_relevant", "stage_id")
    def _compute_visit_intent_allowed(self):
        for lead in self:
            allowed = bool(lead.x_lead_relevant)
            if lead.stage_id and lead.stage_id.name == "Churned":
                allowed = False
            lead.x_can_capture_visit_intent = allowed

    @api.onchange("x_disposition_id")
    def _onchange_visit_intent_allowed(self):
        for lead in self:
            if lead.x_can_capture_visit_intent:
                continue
            if lead.x_visit_intent or lead.x_preferred_clinic_id or lead.x_preferred_visit_date or lead.x_preferred_appointment_type_id:
                lead.x_visit_intent = False
                lead.x_preferred_clinic_id = False
                lead.x_preferred_visit_date = False
                lead.x_preferred_appointment_type_id = False
                return {
                    "warning": {
                        "title": _("Visit Intent Disabled"),
                        "message": _(
                            "Visit Intent is not allowed for non-relevant or churned leads."
                        ),
                    }
                }

    # ============================================================
    # CONSTRAINTS — VISIT INTENT SAFETY
    # ============================================================

    @api.constrains(
        "x_visit_intent",
        "x_lead_relevant",
        "stage_id",
        "x_preferred_clinic_id",
        "x_preferred_visit_date",
    )
    def _check_visit_intent_rules(self):
        """
        Enforces business rules around Visit Intent:
        - Only relevant leads can have visit intent
        - Churned leads cannot have visit intent
        - Clinic & date are mandatory
        """
        for lead in self:
            if not lead.x_visit_intent:
                continue

            if not lead.x_lead_relevant:
                raise ValidationError(
                    _("Visit Intent cannot be set for non-relevant leads.")
                )

            if lead.stage_id and lead.stage_id.name == "Churned":
                raise ValidationError(
                    _("Visit Intent cannot be set for churned leads.")
                )

            if not lead.x_preferred_clinic_id or not lead.x_preferred_visit_date:
                raise ValidationError(
                    _("Preferred Clinic and Visit Date are required.")
                )

    # ============================================================
    # WRITE OVERRIDE — ATTEMPT COUNT, FOLLOW-UP, CHURN
    # ============================================================

    def write(self, vals):
        """
        Handles:
        - lead title sync
        - attempt count increment
        - follow-up activity scheduling
        - churn enforcement

        SAFE for:
        - multi-record writes
        - automated actions
        - future extensions
        """
        vals = dict(vals)
        if not vals.get("name") and any(
            key in vals for key in ("x_phone", "phone", "contact_name", "x_lead_source")
        ):
            vals["name"] = self._build_resonnocare_lead_name(
                {
                    "x_phone": vals.get("x_phone", self[:1].x_phone if self else False),
                    "phone": vals.get("phone", self[:1].phone if self else False),
                    "contact_name": vals.get("contact_name", self[:1].contact_name if self else False),
                    "x_lead_source": vals.get("x_lead_source", self[:1].x_lead_source if self else False),
                }
            )

        disposition_changed = "x_disposition_id" in vals
        old_dispositions = {}
        if disposition_changed:
            old_dispositions = {lead.id: lead.x_disposition_id.id for lead in self}

        result = super().write(vals)

        if disposition_changed:
            for lead in self:
                disposition = lead.x_disposition_id
                if not disposition or old_dispositions.get(lead.id) == disposition.id:
                    continue

                # Increment attempt count
                lead.x_attempt_count += 1

                lead.env["resonnocare.crm.call.log"].sudo().create(
                    {
                        "lead_id": lead.id,
                        "user_id": self.env.user.id,
                        "disposition_id": disposition.id,
                        "attempt_number": lead.x_attempt_count,
                        "lead_relevant": lead.x_lead_relevant,
                        "next_followup_date": lead.x_next_followup_date,
                    }
                )

                # Schedule follow-up activity if applicable
                if disposition.lead_relevant and disposition.follow_up_days > 0:
                    lead._schedule_followup_activity(disposition)

                # Enforce churn if max attempts reached
                if (
                    not disposition.lead_relevant
                    and disposition.max_attempts > 0
                    and lead.x_attempt_count >= disposition.max_attempts
                ):
                    lead._move_to_churned()

        return result

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _schedule_followup_activity(self, disposition):
        """
        Creates a follow-up call activity based on disposition rules.
        """
        self.ensure_one()

        activity_type = self.env.ref(
            "mail.mail_activity_data_call", raise_if_not_found=False
        )
        if not activity_type:
            return

        deadline = fields.Date.today() + timedelta(days=disposition.follow_up_days)

        self.activity_schedule(
            activity_type_id=activity_type.id,
            date_deadline=deadline,
            summary=_("Follow-up: %s") % disposition.name,
            note=_("Scheduled automatically based on call disposition."),
            user_id=self.user_id.id or self.env.user.id,
        )

    def _move_to_churned(self):
        """
        Moves the lead to the 'Churned' stage when max attempts are exhausted.
        """
        self.ensure_one()

        churned_stage = self._get_or_create_churned_stage()

        if churned_stage and self.stage_id != churned_stage:
            self.stage_id = churned_stage.id
            self.message_post(
                body=_(
                    "Lead automatically moved to Churned after maximum follow-up attempts."
                )
            )
        if churned_stage:
            self._create_or_update_churn_campaign()

    def _get_or_create_churned_stage(self):
        self.ensure_one()
        stage_model = self.env["crm.stage"].sudo()
        churned_stage = stage_model.search([("name", "=", "Churned")], limit=1)
        if churned_stage:
            return churned_stage
        return stage_model.create(
            {
                "name": "Churned",
                "sequence": 999,
                "fold": True,
            }
        )

    def _create_or_update_churn_campaign(self):
        self.ensure_one()
        churned_on = fields.Datetime.now()
        tenure_days = 0
        if self.create_date:
            created_date = fields.Date.to_date(self.create_date)
            today = fields.Date.context_today(self)
            tenure_days = max((today - created_date).days, 0)

        campaign_vals = {
            "lead_id": self.id,
            "assigned_agent_id": self.user_id.id,
            "disposition_id": self.x_disposition_id.id,
            "stage_id": self.stage_id.id,
            "interested_clinic_id": self.x_interested_clinic_id.id,
            "preferred_clinic_id": self.x_preferred_clinic_id.id,
            "lead_source": self.x_lead_source,
            "lead_phone": self.x_phone,
            "tenure_days": tenure_days,
            "churned_on": churned_on,
        }
        campaign = self.env["resonnocare.crm.churn.campaign"].sudo().search(
            [("lead_id", "=", self.id)],
            limit=1,
        )
        if campaign:
            campaign.write(campaign_vals)
            return campaign
        return self.env["resonnocare.crm.churn.campaign"].sudo().create(campaign_vals)

    def action_create_appointment_from_lead(self):
        self.ensure_one()
        action = self.env.ref(
            "resonnocare_appointment.action_resonnocare_appointment",
            raise_if_not_found=False,
        )
        if not action or not self.x_patient_id:
            return False

        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_patient_id": self.x_patient_id.id,
                "default_clinic_id": self.x_preferred_clinic_id.id or False,
                "default_appointment_type_id": self.x_preferred_appointment_type_id.id
                or False,
                "default_appointment_date": self.x_preferred_visit_date or False,
                "default_source": "crm",
                "default_crm_lead_id": self.id,
            }
        )
        action_vals = action.sudo().read()[0]
        action_vals.update(
            {
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
                "context": ctx,
            }
        )
        return action_vals

    def action_open_patient_registration_from_lead(self):
        self.ensure_one()
        action = self.env.ref(
            "resonnocare_frontdesk.action_open_patient_registration",
            raise_if_not_found=False,
        )
        if not action:
            return False

        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_crm_lead_id": self.id,
                "default_phone": self.x_phone,
                "default_name": self.contact_name or self.partner_name or self.name,
                "default_referral_source": "crm",
                "default_visit_type": "new",
            }
        )
        action_vals = action.sudo().read()[0]
        action_vals["context"] = ctx
        return action_vals

    def action_open_converted_patient(self):
        self.ensure_one()
        if not self.x_patient_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Patient"),
            "res_model": "res.partner",
            "res_id": self.x_patient_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_booked_appointment(self):
        self.ensure_one()
        if not self.x_appointment_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Appointment"),
            "res_model": "resonnocare.appointment",
            "res_id": self.x_appointment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_converted_to_patient(self, patient):
        self.ensure_one()
        if not patient:
            return

        actor_name = self.env.context.get("conversion_actor_name") or self.env.user.name
        converted_stage = self.env["crm.stage"].search(
            [("name", "=", "Converted")], limit=1
        )
        vals = {
            "x_patient_id": patient.id,
            "x_converted_to_patient": True,
            "x_conversion_datetime": fields.Datetime.now(),
        }
        if converted_stage:
            vals["stage_id"] = converted_stage.id
        self.sudo().write(vals)
        self.sudo().message_post(
            body=_("Lead converted to patient %(patient)s by %(user)s.")
            % {"patient": patient.name, "user": actor_name}
        )
