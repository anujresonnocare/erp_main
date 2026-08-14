from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = "res.users"
    _SELF_RESTRICTED_PREFERENCE_FIELDS = {
        "email",
        "property_warehouse_id",
        "calendar_default_privacy",
    }
    _SELF_SAFE_WRITE_FIELDS = {
        # Native preference/login flow fields
        "login_date",
        "tz",
        "lang",
        "action_id",
        "notification_type",
        "chatter_position",
        "signature",
        "image_1920",
        "avatar_1920",
    }

    resonnocare_alternate_mobile = fields.Char(
        related="employee_id.alternate_mobile",
        readonly=False,
    )
    resonnocare_employee_name = fields.Char(
        string="Employee Name",
        compute="_compute_resonnocare_employee_display",
    )
    resonnocare_work_email = fields.Char(
        string="Work Email",
        compute="_compute_resonnocare_employee_display",
    )
    resonnocare_work_phone = fields.Char(
        string="Work Phone",
        compute="_compute_resonnocare_employee_display",
    )
    resonnocare_employee_code = fields.Char(
        related="employee_id.resonnocare_employee_code",
        readonly=True,
    )
    resonnocare_clinic_name = fields.Char(
        string="Assigned Clinic",
        compute="_compute_resonnocare_employee_display",
    )
    resonnocare_clinic_role = fields.Selection(
        selection=[
            ("front_desk", "Front Desk"),
            ("doctor", "Audiologist"),
            ("technician", "Technician"),
            ("call_centre", "Call Centre"),
        ],
        string="Role",
        compute="_compute_resonnocare_employee_display",
    )
    resonnocare_profile = fields.Selection(
        related="employee_id.resonnocare_profile",
        readonly=True,
    )
    resonnocare_private_phone = fields.Char(
        string="Private Phone",
        compute="_compute_resonnocare_private_phone",
        inverse="_inverse_resonnocare_private_phone",
    )
    resonnocare_private_email = fields.Char(
        string="Private Email",
        compute="_compute_resonnocare_private_email",
        inverse="_inverse_resonnocare_private_email",
    )
    resonnocare_blood_group = fields.Selection(
        selection=[
            ("a_pos", "A+"),
            ("a_neg", "A-"),
            ("b_pos", "B+"),
            ("b_neg", "B-"),
            ("ab_pos", "AB+"),
            ("ab_neg", "AB-"),
            ("o_pos", "O+"),
            ("o_neg", "O-"),
        ],
        related="employee_id.blood_group",
        readonly=False,
    )
    resonnocare_emergency_contact_name = fields.Char(
        related="employee_id.emergency_contact_name",
        readonly=False,
    )
    resonnocare_emergency_contact_number = fields.Char(
        related="employee_id.emergency_contact_number",
        readonly=False,
    )
    resonnocare_emergency_contact_relation = fields.Char(
        related="employee_id.emergency_contact_relation",
        readonly=False,
    )
    resonnocare_onboarding_status = fields.Selection(
        related="employee_id.onboarding_status",
        readonly=True,
    )
    resonnocare_handbook_accepted = fields.Boolean(
        related="employee_id.onboarding_handbook_accepted",
        readonly=True,
    )
    resonnocare_contract_ready = fields.Boolean(
        related="employee_id.onboarding_contract_ready",
        readonly=True,
    )
    resonnocare_contract_status = fields.Selection(
        [
            ("running", "Running"),
            ("not_running", "Not Running"),
        ],
        string="Contract Status",
        compute="_compute_resonnocare_contract_status",
    )
    resonnocare_profile_complete = fields.Boolean(
        related="employee_id.onboarding_profile_complete",
        readonly=True,
    )
    resonnocare_profile_missing_fields = fields.Char(
        related="employee_id.onboarding_profile_missing_fields",
        readonly=True,
    )
    resonnocare_joining_stage_state = fields.Selection(
        related="employee_id.onboarding_joining_stage_state",
        readonly=True,
    )
    resonnocare_attendance_ready = fields.Boolean(
        related="employee_id.onboarding_attendance_ready",
        readonly=True,
    )
    resonnocare_attendance_guide_url = fields.Char(
        string="Attendance Guide URL",
        compute="_compute_resonnocare_attendance_guide",
    )
    resonnocare_attendance_guide_note = fields.Text(
        string="Attendance Guide Note",
        compute="_compute_resonnocare_attendance_guide",
    )
    resonnocare_today_attendance_status = fields.Selection(
        [
            ("present", "Full Day Present"),
            ("half_day", "Half Day Present"),
            ("absent", "Absent"),
            ("holiday", "Holiday / Week-Off"),
        ],
        string="Today's Attendance Status",
        compute="_compute_resonnocare_today_attendance_alert",
    )
    resonnocare_today_deduction_alert = fields.Selection(
        [("yes", "! Deduction Triggered")],
        string="Today's Deduction Alert",
        compute="_compute_resonnocare_today_attendance_alert",
    )
    resonnocare_today_deduction_reason = fields.Char(
        string="Today's Deduction Reason",
        compute="_compute_resonnocare_today_attendance_alert",
    )
    resonnocare_education_ids = fields.One2many(
        related="employee_id.resonnocare_education_ids",
        readonly=False,
    )
    resonnocare_experience_ids = fields.One2many(
        related="employee_id.resonnocare_experience_ids",
        readonly=False,
    )
    resonnocare_license_ids = fields.One2many(
        related="employee_id.resonnocare_license_ids",
        readonly=False,
    )
    resonnocare_dependent_ids = fields.One2many(
        related="employee_id.resonnocare_dependent_ids",
        readonly=False,
    )
    resonnocare_overall_experience_years = fields.Float(
        related="employee_id.resonnocare_overall_experience_years",
        readonly=True,
    )
    resonnocare_relevant_experience_years = fields.Float(
        related="employee_id.resonnocare_relevant_experience_years",
        readonly=False,
    )

    @api.model
    def _get_login_domain(self, login):
        """Allow case-insensitive username/email login."""
        login = (login or "").strip()
        if not login:
            return super()._get_login_domain(login)
        return [("login", "=ilike", login)]

    @api.model
    def _get_email_domain(self, email):
        """Keep password-reset / email lookup case-insensitive as well."""
        email = (email or "").strip()
        if not email:
            return super()._get_email_domain(email)
        return [("email", "=ilike", email)]

    def write(self, vals):
        is_self_only = set(self.ids) == {self.env.uid}
        is_hr_or_super_admin = self.env.user.has_group(
            "resonnocare_base.group_resonnocare_hr"
        ) or self.env.user.has_group("resonnocare_base.group_resonnocare_super_admin")

        # With restrictive custom ACL on res.users, allow controlled self-updates
        # needed for login/preferences/onboarding routing by sudoing only safe fields.
        if is_self_only and not is_hr_or_super_admin and set(vals).issubset(
            self._SELF_SAFE_WRITE_FIELDS
        ):
            return super(ResUsers, self.sudo()).write(vals)

        # Prevent non-HR users from changing controlled profile preferences on self.
        if set(vals).intersection(self._SELF_RESTRICTED_PREFERENCE_FIELDS):
            if is_self_only and not is_hr_or_super_admin:
                raise AccessError(
                    _(
                        "You cannot modify Email, Default Warehouse, or Calendar Default Privacy. "
                        "Please contact HR."
                    )
                )
        return super().write(vals)

    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        is_hr_or_super_admin = self.env.user.has_group(
            "resonnocare_base.group_resonnocare_hr"
        ) or self.env.user.has_group("resonnocare_base.group_resonnocare_super_admin")
        if not is_hr_or_super_admin:
            for field_name in self._SELF_RESTRICTED_PREFERENCE_FIELDS:
                if field_name in result:
                    result[field_name]["readonly"] = True
        return result

    @api.model
    def action_get(self):
        action = super().action_get()
        user = self.env.user
        if user.has_group("resonnocare_base.group_resonnocare_hr") or user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        ):
            return action

        employee = user.sudo().employee_id
        if not employee:
            return action

        my_profile_action = self.env.ref(
            "resonnocare_hr.action_resonnocare_my_profile",
            raise_if_not_found=False,
        )
        if not my_profile_action:
            return action

        action_vals = my_profile_action.sudo().read()[0]
        action_vals["res_id"] = user.id
        return action_vals

    def _check_credentials(self, password, user_agent_env):
        result = super()._check_credentials(password, user_agent_env)
        # Login-time self-healing: ensure onboarding routing action is synced
        # for the authenticating user, including stale action_id repairs.
        for user in self:
            employee = user.sudo().employee_id
            if employee:
                employee._sync_handbook_home_action()
        return result

    def _can_edit_self_onboarding_profile(self):
        self.ensure_one()
        return bool(
            self.id == self.env.uid
            or self.env.user.has_group("resonnocare_base.group_resonnocare_hr")
            or self.env.user.has_group("resonnocare_base.group_resonnocare_super_admin")
        )

    def _compute_resonnocare_private_phone(self):
        for user in self:
            employee = user.sudo().employee_id
            user.resonnocare_private_phone = employee.private_phone if employee else False

    def _inverse_resonnocare_private_phone(self):
        for user in self:
            if not user._can_edit_self_onboarding_profile():
                raise AccessError(
                    _("You can only edit your own onboarding profile fields.")
                )
            employee = user.sudo().employee_id
            if employee:
                employee.sudo().write(
                    {"private_phone": (user.resonnocare_private_phone or "").strip()}
                )

    def _compute_resonnocare_private_email(self):
        for user in self:
            employee = user.sudo().employee_id
            user.resonnocare_private_email = employee.private_email if employee else False

    def _inverse_resonnocare_private_email(self):
        for user in self:
            if not user._can_edit_self_onboarding_profile():
                raise AccessError(
                    _("You can only edit your own onboarding profile fields.")
                )
            employee = user.sudo().employee_id
            if employee:
                employee.sudo().write(
                    {"private_email": (user.resonnocare_private_email or "").strip()}
                )

    def _compute_resonnocare_employee_display(self):
        for user in self:
            employee = user.sudo().employee_id
            user.resonnocare_employee_name = (
                employee.name if employee and employee.name else user.name
            )
            user.resonnocare_work_email = (
                employee.work_email if employee and employee.work_email else user.login
            )
            user.resonnocare_work_phone = (
                employee.work_phone if employee and employee.work_phone else False
            )
            user.resonnocare_clinic_name = (
                employee.clinic_id.name if employee and employee.clinic_id else False
            )
            user.resonnocare_clinic_role = (
                employee.clinic_role if employee and employee.clinic_role else False
            )

    def _compute_resonnocare_contract_status(self):
        has_contract_model = "hr.contract" in self.env
        for user in self:
            employee = user.sudo().employee_id
            status = "not_running"
            if has_contract_model and employee:
                contract_model = self.env["hr.contract"].sudo()
                domain = [("state", "=", "open"), ("employee_id", "=", employee.id)]
                if user.id:
                    domain = [
                        ("state", "=", "open"),
                        "|",
                        ("employee_id", "=", employee.id),
                        ("employee_id.user_id", "=", user.id),
                    ]
                if "active" in contract_model._fields:
                    has_running = bool(
                        contract_model.with_context(active_test=False).search_count(domain)
                    )
                else:
                    has_running = bool(contract_model.search_count(domain))
                if has_running:
                    status = "running"
            user.resonnocare_contract_status = status

    def _compute_resonnocare_attendance_guide(self):
        policy = self.env["resonnocare.attendance.policy"].sudo().search(
            [("active", "=", True)],
            order="priority asc, id asc",
            limit=1,
        )
        params = self.env["ir.config_parameter"].sudo()
        default_note = _(
            "Attendance is activated. Please follow the attendance app/user manual shared by HR."
        )
        guide_url = (
            (policy.attendance_manual_url if policy else False)
            or params.get_param("resonnocare_hr.attendance_guide_url", default="")
            or ""
        )
        guide_note = (
            (policy.attendance_manual_note if policy else False)
            or params.get_param("resonnocare_hr.attendance_guide_note", default=default_note)
            or default_note
        )
        for user in self:
            if user.resonnocare_attendance_ready:
                user.resonnocare_attendance_guide_url = guide_url
                user.resonnocare_attendance_guide_note = guide_note
            else:
                user.resonnocare_attendance_guide_url = False
                user.resonnocare_attendance_guide_note = False

    def _compute_resonnocare_today_attendance_alert(self):
        summary_model = self.env["resonnocare.attendance.summary"].sudo()
        today = fields.Date.context_today(self)
        for user in self:
            user.resonnocare_today_attendance_status = False
            user.resonnocare_today_deduction_alert = False
            user.resonnocare_today_deduction_reason = False

            employee = user.sudo().employee_id
            if not employee:
                continue

            summary = summary_model.search(
                [("employee_id", "=", employee.id), ("date", "=", today)],
                limit=1,
            )
            if not summary:
                continue

            user.resonnocare_today_attendance_status = summary.status
            user.resonnocare_today_deduction_alert = summary.deduction_alert
            user.resonnocare_today_deduction_reason = summary.deduction_alert_reason

    def action_complete_onboarding(self):
        self.ensure_one()
        if self.id != self.env.uid:
            raise AccessError(_("You can only complete onboarding for your own profile."))

        employee = self.employee_id
        if not employee:
            raise AccessError(_("No employee record is linked to your user."))

        # Re-evaluate and enforce mandatory self-service profile completion.
        employee._compute_onboarding_compliance()
        if employee.onboarding_status != "completed":
            missing = employee.onboarding_profile_missing_fields or _("required details")
            raise AccessError(
                _("Please complete your profile before continuing. Missing: %s") % missing
            )

        employee._sync_handbook_home_action()
        return {"type": "ir.actions.act_url", "url": "/odoo", "target": "self"}
