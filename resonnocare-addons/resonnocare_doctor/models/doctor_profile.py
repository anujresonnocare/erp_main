from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class ResonnocareDoctorProfile(models.Model):
    _name = "resonnocare.doctor.profile"
    _description = "External Doctor Profile"
    _rec_name = "name"

    name = fields.Char(string="Doctor Name", required=True, tracking=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_review", "Under Review"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="draft",
        required=True,
        tracking=True,
    )
    team_source = fields.Selection(
        [("hr", "HR"), ("marketing", "Marketing")],
        string="Created By Team",
        default="hr",
        required=True,
    )
    request_date = fields.Date(string="Date of Request")
    abm_name = fields.Char(string="ABM Name")
    change_type = fields.Selection(
        [("addition", "Addition"), ("deletion", "Deletion")],
        string="Addition or Deletion",
        default="addition",
        required=True,
    )
    effective_date = fields.Date(string="Effective Date")
    city = fields.Char(string="Town/City")
    region_name = fields.Char(string="Region Name")
    mobile = fields.Char(string="Mobile Number", tracking=True)
    email = fields.Char(string="Email", required=True, tracking=True)
    enrolment_date = fields.Date(string="Enrolment Date")
    doctor_type = fields.Selection(
        [("ent", "ENT"), ("gp", "GP"), ("outreach", "OUTREACH")],
        string="Type of Doctor",
        tracking=True,
    )
    clinic_address = fields.Text(string="Clinic/Hospital Address")
    remarks = fields.Text(string="Remarks")

    payee_name = fields.Char(string="Payee Name")
    payee_pan_number = fields.Char(string="PAN Number of Payee")
    payee_aadhaar_number = fields.Char(string="AADHAR Number of Payee")
    address_proof_file = fields.Binary(string="Address Proof", attachment=True)
    address_proof_filename = fields.Char(string="Address Proof Filename")
    pan_card_file = fields.Binary(string="PAN Card Copy", attachment=True)
    pan_card_filename = fields.Char(string="PAN Card Filename")
    aadhaar_card_file = fields.Binary(string="AADHAR Card Copy", attachment=True)
    aadhaar_card_filename = fields.Char(string="AADHAR Card Filename")

    bank_account_number = fields.Char(string="Account Number")
    bank_account_type = fields.Selection(
        [("savings", "Savings"), ("current", "Current")],
        string="Account Type",
    )
    bank_name = fields.Char(string="Bank Name")
    bank_address = fields.Text(string="Bank Address")
    bank_ifsc_code = fields.Char(string="IFSC Code")
    cancelled_cheque_file = fields.Binary(
        string="Cancelled Cheque Copy", attachment=True
    )
    cancelled_cheque_filename = fields.Char(string="Cancelled Cheque Filename")
    bank_statement_file = fields.Binary(string="Bank Statement Copy", attachment=True)
    bank_statement_filename = fields.Char(string="Bank Statement Filename")
    passbook_copy_file = fields.Binary(string="Passbook Copy", attachment=True)
    passbook_copy_filename = fields.Char(string="Passbook Copy Filename")

    supported_clinic_ids = fields.Many2many(
        "resonnocare.clinic",
        "resonnocare_doctor_profile_clinic_rel",
        "doctor_id",
        "clinic_id",
        string="Supported Clinics",
    )
    supported_clinic_names = fields.Char(
        string="Supported Clinic List",
        compute="_compute_supported_clinic_names",
    )
    use_different_sharing_by_clinic = fields.Boolean(default=False)
    apply_same_settings_all_clinics = fields.Boolean(
        string="Apply Same Settings For All Clinics",
        compute="_compute_apply_same_settings_all_clinics",
        inverse="_inverse_apply_same_settings_all_clinics",
    )
    different_sharing_clinic_ids = fields.Many2many(
        "resonnocare.clinic",
        "resonnocare_doctor_profile_diff_clinic_rel",
        "doctor_id",
        "clinic_id",
        string="Different Sharing Clinics",
    )
    doctor_sharing_rule_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Doctor Sharing Rules",
    )
    selectable_standard_clinic_ids = fields.Many2many(
        "resonnocare.clinic",
        compute="_compute_selectable_standard_clinic_ids",
        string="Selectable Standard Clinics",
    )
    doctor_sharing_standard_flat_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Standard Flat Rules",
        domain=[("apply_scope", "=", "standard"), ("rule_level", "=", "flat")],
    )
    doctor_sharing_standard_mrp_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Standard MRP Rules",
        domain=[("apply_scope", "=", "standard"), ("rule_level", "=", "mrp")],
    )
    doctor_sharing_standard_item_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Standard Item Rules",
        domain=[("apply_scope", "=", "standard"), ("rule_level", "=", "item")],
    )
    doctor_sharing_standard_source_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Standard Source Rules",
        domain=[("apply_scope", "=", "standard"), ("rule_level", "=", "source")],
    )
    doctor_sharing_different_flat_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Different Flat Rules",
        domain=[("apply_scope", "=", "different"), ("rule_level", "=", "flat")],
    )
    doctor_sharing_different_mrp_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Different MRP Rules",
        domain=[("apply_scope", "=", "different"), ("rule_level", "=", "mrp")],
    )
    doctor_sharing_different_item_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Different Item Rules",
        domain=[("apply_scope", "=", "different"), ("rule_level", "=", "item")],
    )
    doctor_sharing_different_source_ids = fields.One2many(
        "resonnocare.doctor.sharing.rule",
        "doctor_id",
        string="Different Source Rules",
        domain=[("apply_scope", "=", "different"), ("rule_level", "=", "source")],
    )
    enable_flat_sharing = fields.Boolean(default=False)
    enable_mrp_slab_sharing = fields.Boolean(default=False)
    enable_item_based_sharing = fields.Boolean(default=False)
    enable_source_based_sharing = fields.Boolean(default=False)
    sharing_applicable_from = fields.Date()
    sharing_applicable_to = fields.Date()
    agreed_doctor_expense = fields.Monetary(
        string="Agreed Doctor Expense", currency_field="currency_id"
    )
    request_reviewed_by = fields.Char(string="Request Reviewed By (Sales Head)")
    final_approved_by = fields.Char(string="Final Approved By")
    approval_date = fields.Date(string="Approval Date")
    approver_remarks = fields.Text(string="Approver Remarks")

    user_id = fields.Many2one(
        "res.users", string="Login User", readonly=True, copy=False
    )

    commission_ha_percent = fields.Float(
        string="Commission % on Net HA Sales", default=0.0
    )
    commission_diagnostic_percent = fields.Float(
        string="Commission % on Net Diagnostic Revenue", default=0.0
    )

    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    patient_ids = fields.One2many(
        "res.partner",
        "referring_doctor_id",
        string="Patients",
        readonly=True,
    )
    sale_order_ids = fields.One2many(
        "sale.order",
        "referring_doctor_id",
        string="Sales Orders",
        readonly=True,
    )
    patient_count = fields.Integer(compute="_compute_doctor_metrics")
    sale_count = fields.Integer(compute="_compute_doctor_metrics")
    commission_total = fields.Monetary(
        string="Total Commission",
        currency_field="currency_id",
        compute="_compute_doctor_metrics",
    )

    def _register_hook(self):
        result = super()._register_hook()
        self._cleanup_legacy_my_profile_entries()
        self._sync_existing_external_doctor_links()
        self.sudo().search([])._sync_login_access_by_state()
        self._apply_default_menu_sequence()
        return result

    @api.model
    def _cleanup_legacy_my_profile_entries(self):
        legacy_xmlids = [
            "resonnocare_frontdesk.action_resonnocare_my_doctor_profile",
            "resonnocare_frontdesk.menu_external_doctor_my_profile",
        ]
        for xmlid in legacy_xmlids:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec:
                rec.sudo().unlink()

    @api.model
    def _sync_existing_external_doctor_links(self):
        doctor_group = self.env.ref(
            "resonnocare_base.group_external_doctor", raise_if_not_found=False
        )
        base_user_group = self.env.ref("base.group_user", raise_if_not_found=False)
        if not doctor_group:
            return
        users = (
            self.env["res.users"].sudo().search([("groups_id", "in", doctor_group.id)])
        )
        if not users:
            return
        for user in users:
            vals = {}
            if base_user_group:
                vals.setdefault("groups_id", []).append((4, base_user_group.id))
            vals.setdefault("groups_id", []).append((4, doctor_group.id))
            profile = user.external_doctor_profile_id
            if not profile:
                profile = self.sudo().search(
                    [
                        "|",
                        ("user_id", "=", user.id),
                        "|",
                        ("email", "=", user.login),
                        ("email", "=", user.email),
                    ],
                    limit=1,
                )
                if profile:
                    vals["external_doctor_profile_id"] = profile.id
            if vals:
                user.write(vals)
            if profile and profile.user_id != user:
                profile.user_id = user.id

    @api.model
    def _apply_default_menu_sequence(self):
        doctor_menu = self.env.ref(
            "resonnocare_doctor.menu_external_doctor_root",
            raise_if_not_found=False,
        )
        if doctor_menu and doctor_menu.sequence != -100:
            doctor_menu.sudo().write({"sequence": -100})

        hr_menu = self.env.ref("hr.menu_hr_root", raise_if_not_found=False)
        if hr_menu and hr_menu.sequence != 1:
            hr_menu.sudo().write({"sequence": 1})

    @api.depends(
        "patient_ids", "sale_order_ids.state", "sale_order_ids.doctor_commission_amount"
    )
    def _compute_doctor_metrics(self):
        for doctor in self:
            doctor.patient_count = len(doctor.patient_ids)
            confirmed_sales = doctor.sale_order_ids.filtered(
                lambda so: so.state in ("sale", "done")
            )
            doctor.sale_count = len(confirmed_sales)
            doctor.commission_total = sum(
                confirmed_sales.mapped("doctor_commission_amount")
            )

    def _compute_supported_clinic_names(self):
        for doctor in self:
            clinics = doctor.sudo().supported_clinic_ids
            doctor.supported_clinic_names = (
                ", ".join(clinics.mapped("name")) if clinics else False
            )

    def _sharing_all_key(self):
        self.ensure_one()
        return f"resonnocare_doctor.apply_same_settings_all_clinics.{self.id}"

    def _compute_apply_same_settings_all_clinics(self):
        icp = self.env["ir.config_parameter"].sudo()
        for doctor in self:
            if not doctor.id:
                doctor.apply_same_settings_all_clinics = False
                continue
            doctor.apply_same_settings_all_clinics = (
                icp.get_param(doctor._sharing_all_key(), default="0") == "1"
            )

    def _inverse_apply_same_settings_all_clinics(self):
        icp = self.env["ir.config_parameter"].sudo()
        for doctor in self:
            if not doctor.id:
                continue
            icp.set_param(
                doctor._sharing_all_key(),
                "1" if doctor.apply_same_settings_all_clinics else "0",
            )

    @api.depends("apply_same_settings_all_clinics", "supported_clinic_ids")
    def _compute_selectable_standard_clinic_ids(self):
        clinic_model = self.env["resonnocare.clinic"].sudo()
        all_clinics = clinic_model.search([])
        for doctor in self:
            doctor.selectable_standard_clinic_ids = (
                all_clinics
                if doctor.apply_same_settings_all_clinics
                else doctor.supported_clinic_ids
            )

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if any(
            key in vals
            for key in (
                "name",
                "email",
                "supported_clinic_ids",
                "state",
                "change_type",
                "active",
            )
        ):
            self._sync_login_access_by_state()
        return result

    def _is_login_allowed(self):
        self.ensure_one()
        return (
            self.state == "approved" and self.change_type == "addition" and self.active
        )

    def _sync_login_access_by_state(self):
        for doctor in self:
            if doctor._is_login_allowed():
                doctor._ensure_login_user()
            else:
                doctor._deactivate_login_user()

    def _ensure_login_user(self):
        doctor_group = self.env.ref(
            "resonnocare_base.group_external_doctor", raise_if_not_found=False
        )
        base_user_group = self.env.ref("base.group_user", raise_if_not_found=False)
        for doctor in self:
            if not doctor.email:
                continue
            login = doctor.email.strip().lower()
            user_model = self.env["res.users"].sudo()
            user = doctor.user_id.sudo()
            if not user:
                user = user_model.search([("login", "=", login)], limit=1)
                if not user:
                    vals = {
                        "name": doctor.name,
                        "login": login,
                        "email": login,
                        "external_doctor_profile_id": doctor.id,
                        "active": True,
                    }
                    if base_user_group:
                        vals["groups_id"] = [(4, base_user_group.id)]
                    user = user_model.create(vals)
            else:
                if user.login != login:
                    existing = user_model.search([("login", "=", login)], limit=1)
                    if existing and existing != user:
                        user = existing
                user.write(
                    {
                        "name": doctor.name or user.name,
                        "login": login,
                        "email": login,
                        "active": True,
                    }
                )
            commands = []
            if base_user_group:
                commands.append((4, base_user_group.id))
            if doctor_group:
                commands.append((4, doctor_group.id))
            user.sudo().write(
                {
                    "external_doctor_profile_id": doctor.id,
                    "groups_id": commands,
                    "active": True,
                }
            )
            doctor.user_id = user.id

    def _deactivate_login_user(self):
        for doctor in self:
            if doctor.user_id:
                doctor.user_id.sudo().write({"active": False})

    def _resolve_doctor_sharing(self, clinic=False, product=False, mrp=0.0, source_category=False):
        self.ensure_one()
        if not clinic:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }
        today = fields.Date.context_today(self)
        if self.sharing_applicable_from and today < self.sharing_applicable_from:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }
        if self.sharing_applicable_to and today > self.sharing_applicable_to:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }

        billing_type = (
            clinic._get_effective_billing_type()
            if hasattr(clinic, "_get_effective_billing_type")
            else ("b2b" if clinic.clinic_type == "b2b" else "b2c")
        )
        category = clinic._get_product_service_category(product)
        scope = "standard"
        if (
            self.use_different_sharing_by_clinic
            and clinic in self.different_sharing_clinic_ids
        ):
            scope = "different"
        if (
            scope == "standard"
            and not self.apply_same_settings_all_clinics
            and self.supported_clinic_ids
            and clinic not in self.supported_clinic_ids
        ):
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }
        if scope == "different" and clinic not in self.different_sharing_clinic_ids:
            return {
                "sharing_percent": 0.0,
                "billing_price": 0.0,
                "rule_id": False,
                "rule_level": False,
            }

        if scope == "standard" and self.apply_same_settings_all_clinics:
            rules = self.doctor_sharing_rule_ids.filtered(
                lambda r: r.active
                and r.apply_scope == scope
                and (not r.applicable_from or r.applicable_from <= today)
                and (not r.applicable_to or r.applicable_to >= today)
                and r.product_category == category
                and (not r.billing_type or r.billing_type == billing_type)
            )
        else:
            rules = self.doctor_sharing_rule_ids.filtered(
                lambda r: r.active
                and r.apply_scope == scope
                and r.clinic_id == clinic
                and (not r.applicable_from or r.applicable_from <= today)
                and (not r.applicable_to or r.applicable_to >= today)
                and r.product_category == category
                and (not r.billing_type or r.billing_type == billing_type)
            )

        def _pick(level, pred):
            candidates = rules.filtered(lambda r: r.rule_level == level and pred(r))
            if not candidates:
                return False
            exact_billing = candidates.filtered(lambda r: r.billing_type == billing_type)
            return (exact_billing or candidates).sorted(
                key=lambda r: (r.sequence, r.id)
            )[:1]

        level_order = [
            ("source", self.enable_source_based_sharing),
            ("item", self.enable_item_based_sharing),
            ("mrp", self.enable_mrp_slab_sharing),
            ("flat", self.enable_flat_sharing),
        ]
        for level, enabled in level_order:
            if not enabled:
                continue
            match = False
            if level == "source" and source_category:
                match = _pick(level, lambda r: r.source_category == source_category)
            elif level == "item" and product:
                match = _pick(
                    level, lambda r: r.product_tmpl_id and r.product_tmpl_id == product.product_tmpl_id
                )
            elif level == "mrp":
                match = _pick(
                    level,
                    lambda r: (not r.mrp_range_from or mrp >= r.mrp_range_from)
                    and (not r.mrp_range_to or mrp <= r.mrp_range_to),
                )
            elif level == "flat":
                match = _pick(level, lambda r: True)
            if match:
                rule = match[0]
                return {
                    "sharing_percent": rule.sharing_percent or 0.0,
                    "billing_price": rule.billing_price or 0.0,
                    "rule_id": rule.id,
                    "rule_level": rule.rule_level,
                }
        return {
            "sharing_percent": 0.0,
            "billing_price": 0.0,
            "rule_id": False,
            "rule_level": False,
        }

    def action_submit_for_review(self):
        for doctor in self:
            if doctor.state not in ("draft", "rejected"):
                continue
            vals = {"state": "under_review"}
            if not doctor.request_date:
                vals["request_date"] = fields.Date.today()
            doctor.write(vals)
        self._sync_login_access_by_state()
        return True

    def action_mark_reviewed(self):
        for doctor in self:
            if doctor.state not in ("under_review", "draft"):
                continue
            vals = {"state": "reviewed", "request_reviewed_by": self.env.user.name}
            doctor.write(vals)
        self._sync_login_access_by_state()
        return True

    def action_approve(self):
        for doctor in self:
            if doctor.state not in ("reviewed", "under_review"):
                continue
            vals = {
                "state": "approved",
                "final_approved_by": self.env.user.name,
                "approval_date": fields.Date.today(),
            }
            if doctor.change_type == "deletion":
                vals["active"] = False
            else:
                vals["active"] = True
            doctor.write(vals)
        self._sync_login_access_by_state()
        return True

    def action_reject(self):
        for doctor in self:
            doctor.write({"state": "rejected", "final_approved_by": self.env.user.name})
        self._sync_login_access_by_state()
        return True

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
        self._sync_login_access_by_state()
        return True

    @api.model
    def action_open_my_profile(self):
        user = self.env.user
        profile = user.external_doctor_profile_id
        if not profile:
            profile = self.sudo().search(
                [
                    "|",
                    ("user_id", "=", user.id),
                    "|",
                    ("email", "=", user.login),
                    ("email", "=", user.email),
                ],
                limit=1,
            )
        if not profile:
            raise UserError(
                "Your doctor profile is not configured. Please contact HR/Marketing."
            )

        view = self.env.ref(
            "resonnocare_doctor.view_resonnocare_doctor_profile_kanban_my_profile"
        )
        return {
            "type": "ir.actions.act_window",
            "name": "My Profile",
            "res_model": "resonnocare.doctor.profile",
            "view_mode": "kanban",
            "views": [(view.id, "kanban")],
            "domain": [("id", "=", profile.id)],
            "target": "current",
            "context": {"create": 0, "edit": 0, "delete": 0},
        }

    @api.constrains("commission_ha_percent", "commission_diagnostic_percent")
    def _check_commission_range(self):
        for doctor in self:
            if not (0 <= doctor.commission_ha_percent <= 100):
                raise ValidationError(
                    "Commission % on Net HA Sales must be between 0 and 100."
                )
            if not (0 <= doctor.commission_diagnostic_percent <= 100):
                raise ValidationError(
                    "Commission % on Net Diagnostic Revenue must be between 0 and 100."
                )
