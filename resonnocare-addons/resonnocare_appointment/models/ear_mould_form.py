# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date


class ResonnocareEarMouldForm(models.Model):
    _name = "resonnocare.ear.mould.form"
    _description = "Ear Mould Order Form"
    _order = "id desc"
    _sql_constraints = [
        ("uniq_device_line_form", "unique(device_line_id)", "Ear Mould Form already exists for this device line."),
    ]

    name = fields.Char(string="Order ID", readonly=True, copy=False, default="/")
    order_date = fields.Date(string="Date", default=fields.Date.today, required=True)

    appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Appointment",
        required=True,
        ondelete="cascade",
    )
    device_line_id = fields.Many2one(
        "resonnocare.appointment.device.line",
        string="Device Line",
        required=True,
        ondelete="cascade",
    )

    patient_id = fields.Many2one(related="appointment_id.patient_id", string="Patient", store=True, readonly=True)
    patient_code = fields.Char(related="patient_id.patient_id", string="Patient ID", store=True, readonly=True)
    clinic_id = fields.Many2one(related="appointment_id.clinic_id", string="Clinic", store=True, readonly=True)
    audiologist_id = fields.Many2one(related="appointment_id.audiologist_id", string="Audiologist", store=True, readonly=True)
    can_number = fields.Char(
        related="device_line_id.product_id.product_tmpl_id.can_number",
        string="CAN Number",
        store=True,
        readonly=True,
    )

    order_type = fields.Selection(
        [
            ("new_mould", "New Mould"),
            ("new_custom_model", "New Custom Model"),
            ("reshell_remake", "Re-shell / Remake"),
            ("repair", "Repair"),
        ],
        string="Order Type",
        required=True,
        default="new_mould",
    )

    vendor_name_address = fields.Text(string="Vendor Name & Address")
    clinic_name_address = fields.Text(string="Resonnocare Clinic Name & Address")

    patient_age_sex = fields.Char(string="Patient Age / Sex")
    first_time_user = fields.Selection([("yes", "Yes"), ("no", "No")], string="First Time User")
    most_important = fields.Selection(
        [("cosmetic", "Cosmetic"), ("comfort", "Comfort")],
        string="Most Important",
    )

    right_250 = fields.Float(string="Right 250Hz")
    right_500 = fields.Float(string="Right 500Hz")
    right_1000 = fields.Float(string="Right 1000Hz")
    right_2000 = fields.Float(string="Right 2000Hz")
    right_3000 = fields.Float(string="Right 3000Hz")
    right_4000 = fields.Float(string="Right 4000Hz")
    right_8000 = fields.Float(string="Right 8000Hz")

    left_250 = fields.Float(string="Left 250Hz")
    left_500 = fields.Float(string="Left 500Hz")
    left_1000 = fields.Float(string="Left 1000Hz")
    left_2000 = fields.Float(string="Left 2000Hz")
    left_3000 = fields.Float(string="Left 3000Hz")
    left_4000 = fields.Float(string="Left 4000Hz")
    left_8000 = fields.Float(string="Left 8000Hz")

    right_ear_canal_length = fields.Selection(
        [("long", "Long"), ("medium", "Medium"), ("short", "Short")],
        string="Right Ear Canal Length",
    )
    left_ear_canal_length = fields.Selection(
        [("long", "Long"), ("medium", "Medium"), ("short", "Short")],
        string="Left Ear Canal Length",
    )

    right_mould_vent = fields.Selection([("soft", "Soft"), ("hard", "Hard")], string="Right Ear Mould Vent")
    left_mould_vent = fields.Selection([("soft", "Soft"), ("hard", "Hard")], string="Left Ear Mould Vent")
    right_vent_size = fields.Selection([("small", "Small"), ("medium", "Medium"), ("large", "Large")], string="Right Vent Size")
    left_vent_size = fields.Selection([("small", "Small"), ("medium", "Medium"), ("large", "Large")], string="Left Vent Size")

    mould_type = fields.Selection(
        [
            ("full_concha", "Full Concha"),
            ("half_concha", "Half Concha"),
            ("tip_mould", "Tip Mould"),
            ("hp_micro_mould", "HP Micro Mould"),
            ("rie_micro_mould", "RIE Micro Mould"),
            ("flex_vent_mould", "Flex Vent Mould"),
        ],
        string="Mould Type",
    )

    ha_model_name_right = fields.Char(string="HA Model Name (Right)")
    ha_model_name_left = fields.Char(string="HA Model Name (Left)")

    right_type = fields.Selection([("cic", "CIC"), ("ite", "ITE"), ("itc", "ITC")], string="Right Type")
    left_type = fields.Selection([("cic", "CIC"), ("ite", "ITE"), ("itc", "ITC")], string="Left Type")

    right_volume_control = fields.Boolean(string="Right Volume Control")
    right_switch = fields.Boolean(string="Right Switch")
    right_telecoil = fields.Boolean(string="Right Telecoil")
    left_volume_control = fields.Boolean(string="Left Volume Control")
    left_switch = fields.Boolean(string="Left Switch")
    left_telecoil = fields.Boolean(string="Left Telecoil")

    right_vent_shape = fields.Selection([("small", "Small"), ("medium", "Medium"), ("large", "Large")], string="Right Vent Shape")
    left_vent_shape = fields.Selection([("small", "Small"), ("medium", "Medium"), ("large", "Large")], string="Left Vent Shape")

    right_shell = fields.Selection([("full", "Full Shell"), ("half", "Half Shell")], string="Right Shell")
    left_shell = fields.Selection([("full", "Full Shell"), ("half", "Half Shell")], string="Left Shell")

    remake_shell = fields.Boolean(string="Remake Shell")
    too_tight = fields.Boolean(string="Too Tight")
    too_loose = fields.Boolean(string="Loose")
    add_vent = fields.Boolean(string="Add Vent")
    seal_vent = fields.Boolean(string="Seal Vent")
    make_small_as_possible = fields.Boolean(string="Please make as small as possible")
    vent_size_required = fields.Char(string="Vent Size Required")

    notes = fields.Text(string="Specific Remark / Request")
    audiologist_signature_name = fields.Char(string="Audiologist Name & Signature")

    is_minimum_complete = fields.Boolean(
        string="Minimum Complete",
        compute="_compute_is_minimum_complete",
        store=False,
    )

    @api.depends("order_type", "mould_type")
    def _compute_is_minimum_complete(self):
        for rec in self:
            rec.is_minimum_complete = bool(rec.order_type and rec.mould_type)

    @api.model
    def default_get(self, field_list):
        vals = super().default_get(field_list)
        appointment_id = vals.get("appointment_id") or self.env.context.get("default_appointment_id")
        device_line_id = vals.get("device_line_id") or self.env.context.get("default_device_line_id")
        appointment = self.env["resonnocare.appointment"].browse(appointment_id) if appointment_id else False
        device_line = self.env["resonnocare.appointment.device.line"].browse(device_line_id) if device_line_id else False
        auto_vals = self._prepare_autofill_vals(appointment, device_line)
        for key, value in auto_vals.items():
            if key in field_list and not vals.get(key):
                vals[key] = value
        return vals

    def _compute_age(self, birthdate):
        if not birthdate:
            return ""
        today = date.today()
        years = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return str(max(years, 0))

    def _prepare_autofill_vals(self, appointment, device_line):
        vals = {}
        patient = appointment.patient_id if appointment else False
        clinic = appointment.clinic_id if appointment else False
        product = device_line.product_id if device_line else False

        def _full_address(partner):
            if not partner:
                return ""
            state_name = partner.state_id.name if getattr(partner, "state_id", False) else ""
            parts = [
                partner.display_name,
                partner.street,
                partner.street2,
                partner.city,
                state_name,
                partner.zip,
                partner.country_id.name if getattr(partner, "country_id", False) else "",
                f"Phone: {partner.phone}" if partner.phone else "",
                f"Mobile: {partner.mobile}" if getattr(partner, "mobile", False) else "",
            ]
            return ", ".join([p for p in parts if p])

        if clinic:
            company = clinic.company_id if clinic.company_id else False
            vals["clinic_name_address"] = ", ".join(
                x
                for x in [
                    clinic.display_name,
                    clinic.street,
                    clinic.street2,
                    clinic.city,
                    clinic.state_id.name if clinic.state_id else "",
                    clinic.zip,
                    f"Phone: {company.phone}" if company and company.phone else "",
                ]
                if x
            )
        if appointment and appointment.audiologist_id:
            vals["audiologist_signature_name"] = appointment.audiologist_id.name or ""
        if patient:
            age = self._compute_age(patient.birthdate_date)
            gender = dict(patient._fields["gender"].selection).get(patient.gender, "") if patient.gender else ""
            vals["patient_age_sex"] = " / ".join([x for x in [age, gender] if x])
            if patient.used_hearing_aid_before == "no":
                vals["first_time_user"] = "yes"
            elif patient.used_hearing_aid_before == "yes":
                vals["first_time_user"] = "no"
        if product:
            vals["ha_model_name_right"] = product.display_name
            if (device_line.product_uom_qty or 0.0) >= 2:
                vals["ha_model_name_left"] = product.display_name
            seller = product.product_tmpl_id.seller_ids[:1].partner_id if product.product_tmpl_id.seller_ids else False
            if seller:
                vals["vendor_name_address"] = _full_address(seller)
        return vals

    @api.onchange("appointment_id", "device_line_id")
    def _onchange_autofill(self):
        for rec in self:
            auto_vals = rec._prepare_autofill_vals(rec.appointment_id, rec.device_line_id)
            for key, value in auto_vals.items():
                if key in rec._fields and not rec[key]:
                    rec[key] = value

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = seq.next_by_code("resonnocare.ear.mould.form") or "/"
            appointment = self.env["resonnocare.appointment"].browse(vals.get("appointment_id")) if vals.get("appointment_id") else False
            device_line = self.env["resonnocare.appointment.device.line"].browse(vals.get("device_line_id")) if vals.get("device_line_id") else False
            auto_vals = self._prepare_autofill_vals(appointment, device_line)
            for key, value in auto_vals.items():
                if not vals.get(key):
                    vals[key] = value
        return super().create(vals_list)

    @api.constrains("appointment_id", "device_line_id")
    def _check_device_line_link(self):
        for rec in self:
            if rec.device_line_id.appointment_id != rec.appointment_id:
                raise UserError("Ear Mould Form device line must belong to the same appointment.")

    def action_print_ear_mould_form(self):
        self.ensure_one()
        return self.env.ref("resonnocare_appointment.action_report_ear_mould_form").report_action(self)

    def action_preview_ear_mould_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/pdf/resonnocare_appointment.report_ear_mould_form_document/{self.id}?download=false",
            "target": "self",
        }
