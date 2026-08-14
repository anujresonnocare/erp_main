from datetime import timedelta
import logging

from odoo import api, models, fields, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _SELF_SERVICE_BLOCKED_FIELDS = {
        "user_id",
        "clinic_id",
        "clinic_role",
        "resonnocare_function",
        "resonnocare_region_id",
        "resonnocare_weekly_off_pattern",
        "resonnocare_holiday_calendar_id",
        "attendance_profile",
        "department_id",
        "address_id",
        "work_location_id",
        "job_id",
        "functional_manager_id",
        "joining_date",
        "company_id",
        "resource_calendar_id",
        "attendance_manager_id",
        "parent_id",
        "coach_id",
        "leave_manager_id",
        "employee_type",
        "pin",
        "barcode",
        "work_email",
        "work_phone",
        "mobile_phone",
        "resonnocare_profile",
    }

    _ROLE_TO_GROUP_XMLID = {
        "front_desk": "resonnocare_base.group_front_desk",
        "doctor": "resonnocare_base.group_doctor",
        "technician": "resonnocare_base.group_resonnocare_internal",
        "call_centre": "resonnocare_base.group_crm",
    }

    def _register_hook(self):
        result = super()._register_hook()
        # Backfill/repair onboarding home actions for existing employee users
        # after module upgrades so stale action_id values do not keep routing to /new.
        try:
            self.env.cr.execute(
                """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'hr_employee'
                      AND column_name = 'resonnocare_profile'
                    LIMIT 1
                """
            )
            if not self.env.cr.fetchone():
                return result
            employees = self.sudo().search([("user_id", "!=", False)])
            employees._sync_handbook_home_action()
            employees._sync_user_role_from_employee()
        except Exception as exc:
            # Prevent module load transaction from remaining aborted on startup.
            self.env.cr.rollback()
            _logger.warning("Skipped handbook home-action sync in _register_hook: %s", exc)
        return result

    # Categorization
    attendance_profile = fields.Selection(
        [("fixed", "Fixed"), ("roaming", "Roaming")],
        string="Attendance Profile",
        tracking=True,
    )
    resonnocare_profile = fields.Selection(
        [
            ("management", "Management"),
            ("back_office", "Back Office"),
            ("call_centre", "Call Centre"),
            ("audiologist", "Audiologist"),
            ("technician", "Technician"),
            ("audiologist_leave_support", "Audiologist - Leave Support"),
            ("sales", "Sales"),
        ],
        string="Profile",
        tracking=True,
    )
    resonnocare_master_mapping_ids = fields.One2many(
        "resonnocare.employee.master.mapping",
        "employee_id",
        string="Master Mapping",
    )
    resonnocare_function = fields.Selection(
        [
            ("finance", "Finance"),
            ("hr", "HR"),
            ("it", "IT"),
            ("admin", "Admin"),
            ("marketing", "Marketing"),
            ("supply_chain", "Supply Chain"),
            ("operations", "Operations"),
            ("sales", "Sales"),
            ("other", "Other"),
        ],
        string="Function",
        compute="_compute_resonnocare_master_mapping_fields",
        inverse="_inverse_resonnocare_master_mapping_fields",
    )
    resonnocare_region_id = fields.Many2one(
        "res.country.group",
        string="Region",
        compute="_compute_resonnocare_master_mapping_fields",
        inverse="_inverse_resonnocare_master_mapping_fields",
    )
    resonnocare_weekly_off_pattern = fields.Selection(
        [
            ("sun", "Sunday"),
            ("sat_sun", "Saturday + Sunday"),
            ("rotational", "Rotational"),
            ("none", "No Fixed Weekly Off"),
        ],
        string="Weekly Off Pattern",
        compute="_compute_resonnocare_master_mapping_fields",
        inverse="_inverse_resonnocare_master_mapping_fields",
    )
    resonnocare_holiday_calendar_id = fields.Many2one(
        "resonnocare.holiday.calendar",
        string="Holiday Calendar Mapping",
        compute="_compute_resonnocare_master_mapping_fields",
        inverse="_inverse_resonnocare_master_mapping_fields",
    )
    resonnocare_applicable_holiday_count = fields.Integer(
        string="Applicable Holidays",
        compute="_compute_resonnocare_applicable_holiday_count",
    )

    functional_manager_id = fields.Many2one(
        "hr.employee", string="Disciplinary Manager", tracking=True
    )

    # Related fields derived from Clinic (resonnocare_clinic)
    resonnocare_state_id = fields.Many2one(
        "res.country.state",
        related="clinic_id.state_id",
        string="State",
        readonly=True,
        store=True,
    )
    resonnocare_country_id = fields.Many2one(
        "res.country",
        related="clinic_id.country_id",
        string="Country",
        readonly=True,
        store=True,
    )

    # Personal Details
    alternate_mobile = fields.Char(string="Alternate Mobile Number")
    blood_group = fields.Selection(
        [
            ("a_pos", "A+"),
            ("a_neg", "A-"),
            ("b_pos", "B+"),
            ("b_neg", "B-"),
            ("ab_pos", "AB+"),
            ("ab_neg", "AB-"),
            ("o_pos", "O+"),
            ("o_neg", "O-"),
        ],
        string="Blood Group",
    )

    emergency_contact_name = fields.Char(string="Emergency Contact Name")
    emergency_contact_number = fields.Char(string="Emergency Contact Number")
    emergency_contact_relation = fields.Char(string="Relationship")
    resonnocare_dependent_ids = fields.One2many(
        "resonnocare.hr.dependent",
        "employee_id",
        string="Mediclaim Dependents",
    )

    # Education & Experience
    resonnocare_education_ids = fields.One2many(
        "resonnocare.hr.education", "employee_id", string="Education History"
    )
    resonnocare_experience_ids = fields.One2many(
        "resonnocare.hr.experience", "employee_id", string="Employment History"
    )
    resonnocare_license_ids = fields.One2many(
        "resonnocare.hr.license", "employee_id", string="Professional Licenses"
    )
    resonnocare_overall_experience_years = fields.Float(
        string="Overall Work Experience (Years)",
        compute="_compute_resonnocare_overall_experience_years",
        store=True,
        readonly=True,
    )
    resonnocare_relevant_experience_years = fields.Float(
        string="Relevant Experience (Years)"
    )

    # Employment Details (Joining Date & Type linked to Contract in implementation, but adding placeholders for easy view)
    # Joining date is often used on employee directly for simple tracking
    joining_date = fields.Date(string="Date of Joining", tracking=True)
    resonnocare_employee_code = fields.Char(
        string="Employee ID",
        readonly=True,
        copy=False,
        tracking=True,
    )
    onboarding_handbook_accepted = fields.Boolean(
        string="Handbook Accepted",
        compute="_compute_onboarding_compliance",
    )
    onboarding_handbook_accepted_on = fields.Datetime(
        string="Handbook Accepted On",
        compute="_compute_onboarding_compliance",
    )
    onboarding_handbook_ip = fields.Char(
        string="Handbook Accepted IP",
        compute="_compute_onboarding_compliance",
    )
    onboarding_contract_ready = fields.Boolean(
        string="Contract Ready",
        compute="_compute_onboarding_contract_status",
    )
    onboarding_contract_status = fields.Selection(
        [
            ("running", "Running"),
            ("not_running", "Not Running"),
        ],
        string="Contract Status",
        compute="_compute_onboarding_contract_status",
    )
    onboarding_status = fields.Selection(
        [
            ("pending_handbook", "Pending Handbook Acceptance"),
            ("pending_contract", "Pending Contract Setup"),
            ("pending_profile", "Pending Profile Completion"),
            ("completed", "Completed"),
        ],
        string="Onboarding Status",
        compute="_compute_onboarding_compliance",
    )
    onboarding_profile_complete = fields.Boolean(
        string="Profile Complete",
        compute="_compute_onboarding_compliance",
    )
    onboarding_profile_missing_fields = fields.Char(
        string="Profile Missing Fields",
        compute="_compute_onboarding_compliance",
    )
    onboarding_joining_stage_state = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("initiated", "Initiated"),
            ("activated", "Activated"),
        ],
        string="Joining Stage",
        default="not_started",
        tracking=True,
        copy=False,
    )
    onboarding_joining_stage_initiated_by = fields.Many2one(
        "res.users",
        string="Joining Stage Initiated By",
        readonly=True,
        copy=False,
    )
    onboarding_joining_stage_initiated_on = fields.Datetime(
        string="Joining Stage Initiated On",
        readonly=True,
        copy=False,
    )
    onboarding_joining_stage_activated_by = fields.Many2one(
        "res.users",
        string="Joining Stage Activated By",
        readonly=True,
        copy=False,
    )
    onboarding_joining_stage_activated_on = fields.Datetime(
        string="Joining Stage Activated On",
        readonly=True,
        copy=False,
    )
    onboarding_attendance_ready = fields.Boolean(
        string="Attendance Activated",
        readonly=True,
        copy=False,
    )
    onboarding_attendance_ready_by = fields.Many2one(
        "res.users",
        string="Attendance Activated By",
        readonly=True,
        copy=False,
    )
    onboarding_attendance_ready_on = fields.Datetime(
        string="Attendance Activated On",
        readonly=True,
        copy=False,
    )
    onboarding_uat_status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        string="UAT Status",
        compute="_compute_onboarding_uat_readiness",
    )
    onboarding_uat_pending_count = fields.Integer(
        string="UAT Pending Checks",
        compute="_compute_onboarding_uat_readiness",
    )
    onboarding_production_ready = fields.Boolean(
        string="Production Ready",
        compute="_compute_onboarding_uat_readiness",
    )
    onboarding_production_blockers = fields.Char(
        string="Production Blockers",
        compute="_compute_onboarding_uat_readiness",
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

    @classmethod
    def _is_valid_phone_general(cls, number):
        digits = cls._normalize_phone_digits(number)
        return 10 <= len(digits) <= 15

    @api.constrains(
        "work_phone",
        "mobile_phone",
        "private_phone",
        "alternate_mobile",
        "emergency_contact_number",
    )
    def _check_employee_phone_numbers(self):
        for employee in self:
            if employee.work_phone and not self._is_valid_phone_general(
                employee.work_phone
            ):
                raise ValidationError("Work Phone must contain 10 to 15 digits.")
            for field_name, field_label in [
                ("mobile_phone", "Mobile"),
                ("private_phone", "Private Phone"),
                ("alternate_mobile", "Alternate Mobile Number"),
                ("emergency_contact_number", "Emergency Contact Number"),
            ]:
                value = employee[field_name]
                if value and not self._is_valid_indian_mobile(value):
                    raise ValidationError(
                        _("%s must be a valid 10-digit Indian mobile number.")
                        % field_label
                    )

    def _resonnocare_master_mapping_table_exists(self):
        self.env.cr.execute(
            "SELECT to_regclass('public.resonnocare_employee_master_mapping')"
        )
        row = self.env.cr.fetchone()
        return bool(row and row[0])

    def _get_or_create_master_mapping(self):
        self.ensure_one()
        mapping_model = self.env["resonnocare.employee.master.mapping"].sudo()
        mapping = mapping_model.search([("employee_id", "=", self.id)], limit=1)
        if not mapping:
            mapping = mapping_model.create({"employee_id": self.id})
        return mapping

    @api.depends("resonnocare_master_mapping_ids")
    def _compute_resonnocare_master_mapping_fields(self):
        if not self._resonnocare_master_mapping_table_exists():
            for employee in self:
                employee.resonnocare_function = False
                employee.resonnocare_region_id = False
                employee.resonnocare_weekly_off_pattern = False
                employee.resonnocare_holiday_calendar_id = False
            return

        mapping_model = self.env["resonnocare.employee.master.mapping"].sudo()
        for employee in self:
            mapping = mapping_model.search([("employee_id", "=", employee.id)], limit=1)
            employee.resonnocare_function = mapping.function_name if mapping else False
            employee.resonnocare_region_id = mapping.region_id.id if mapping else False
            employee.resonnocare_weekly_off_pattern = (
                mapping.weekly_off_pattern if mapping else False
            )
            employee.resonnocare_holiday_calendar_id = (
                mapping.holiday_calendar_id.id if mapping else False
            )

    def _compute_resonnocare_applicable_holiday_count(self):
        holiday_model = self.env["resonnocare.holiday.calendar"].sudo()
        for employee in self:
            employee.resonnocare_applicable_holiday_count = len(
                holiday_model.get_applicable_holidays_for_employee(employee.sudo())
            )

    def _inverse_resonnocare_master_mapping_fields(self):
        # Mapping persistence is handled explicitly in write().
        # Keeping inverse non-destructive avoids partial cache writes from clearing
        # sibling mapping fields when only one field is edited in the form.
        return

    def action_open_applicable_holidays(self):
        self.ensure_one()
        holidays = self.env["resonnocare.holiday.calendar"].sudo().get_applicable_holidays_for_employee(
            self.sudo()
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Applicable Holidays"),
            "res_model": "resonnocare.holiday.calendar",
            "view_mode": "list,form",
            "domain": [("id", "in", holidays.ids)],
            "context": {"create": False},
        }

    def _get_resonnocare_holiday_candidate(self):
        self.ensure_one()
        holiday_model = self.env["resonnocare.holiday.calendar"].sudo()
        employee = self.sudo()

        # Specificity: clinic > state > region > global
        domains = []
        if employee.clinic_id:
            domains.append([("active", "=", True), ("scope", "=", "clinic"), ("clinic_id", "=", employee.clinic_id.id)])
        if employee.resonnocare_state_id:
            domains.append([("active", "=", True), ("scope", "=", "state"), ("state_id", "=", employee.resonnocare_state_id.id)])
        if employee.resonnocare_country_id:
            region = self.env["res.country.group"].sudo().search(
                [("country_ids", "in", employee.resonnocare_country_id.id)],
                limit=1,
            )
            if region:
                domains.append([("active", "=", True), ("scope", "=", "region"), ("region_id", "=", region.id)])
        domains.append([("active", "=", True), ("scope", "=", "global")])

        for domain in domains:
            candidate = holiday_model.search(domain, order="date_from desc, id desc", limit=1)
            if candidate:
                return candidate
        return holiday_model

    def _auto_assign_holiday_calendar_mapping(self, force=False):
        if not self._resonnocare_master_mapping_table_exists():
            return
        for employee in self.sudo():
            if employee.resonnocare_holiday_calendar_id and not force:
                continue
            candidate = employee._get_resonnocare_holiday_candidate()
            if not candidate:
                continue
            mapping = employee._get_or_create_master_mapping()
            if mapping.holiday_calendar_id != candidate:
                mapping.write({"holiday_calendar_id": candidate.id})

    def _compute_onboarding_uat_readiness(self):
        for employee in self:
            blockers = []
            if employee.onboarding_joining_stage_state != "activated":
                blockers.append(_("Joining not activated"))
            if employee.onboarding_status != "completed":
                blockers.append(_("Onboarding incomplete"))
            employee.onboarding_uat_status = "completed" if not blockers else "not_started"
            employee.onboarding_uat_pending_count = 0
            employee.onboarding_production_ready = not blockers
            employee.onboarding_production_blockers = ", ".join(blockers) if blockers else False

    def action_validate_production_readiness(self):
        if not self._is_hr_onboarding_actor():
            raise AccessError(_("Only HR can validate production readiness."))
        for employee in self:
            employee._compute_onboarding_compliance()
            employee._compute_onboarding_uat_readiness()
            if not employee.onboarding_production_ready:
                raise UserError(
                    _(
                        "Employee %(employee)s is not production ready. Blockers: %(blockers)s",
                        employee=employee.name,
                        blockers=employee.onboarding_production_blockers or _("Unknown blockers"),
                    )
                )
            employee.message_post(body=_("Production readiness validated by HR."))
        return True
    def _get_profile_missing_fields(self):
        self.ensure_one()
        employee = self.sudo()
        checks = [
            ("private_phone", "Private Phone"),
            ("private_email", "Private Email"),
            ("blood_group", "Blood Group"),
            ("emergency_contact_name", "Emergency Contact Name"),
            ("emergency_contact_number", "Emergency Contact Number"),
            ("emergency_contact_relation", "Emergency Contact Relationship"),
        ]
        return [label for field_name, label in checks if not employee[field_name]]

    def _get_hris_setup_missing_fields(self):
        self.ensure_one()
        employee = self.sudo()
        checks = [
            ("job_id", "Designation"),
            ("resonnocare_profile", "Profile"),
            ("attendance_profile", "Attendance Profile"),
            ("resonnocare_function", "Function"),
            ("resonnocare_region_id", "Region"),
            ("resonnocare_weekly_off_pattern", "Weekly Off Pattern"),
            ("parent_id", "Manager"),
            ("functional_manager_id", "Disciplinary Manager"),
            ("joining_date", "Date of Joining"),
            ("resource_calendar_id", "Shift Assignment"),
            ("employee_type", "Employment Type"),
        ]
        # Admin setup can proceed without an HR designation.
        if employee.resonnocare_function == "admin":
            checks = [item for item in checks if item[0] != "job_id"]
        missing = [label for field_name, label in checks if not employee[field_name]]

        # Clinic/role mapping is mandatory for clinic-facing employees only.
        # HR/Admin can operate without clinic mapping.
        exempt_functions = {"hr", "admin"}
        if employee.resonnocare_function not in exempt_functions:
            if employee.clinic_role == "call_centre":
                if not employee.work_location_id:
                    missing.append("Work Location")
                if "clinic_role" in employee._fields and not employee.clinic_role:
                    missing.append("Clinic Role")
            else:
                if not (employee.clinic_id or employee.work_location_id):
                    missing.append("Clinic / Location")
                if "clinic_role" in employee._fields and not employee.clinic_role:
                    missing.append("Clinic Role")

        return missing

    @api.depends("resonnocare_experience_ids.start_date", "resonnocare_experience_ids.end_date")
    def _compute_resonnocare_overall_experience_years(self):
        today = fields.Date.context_today(self)
        for employee in self:
            total_days = 0
            for line in employee.resonnocare_experience_ids:
                if not line.start_date:
                    continue
                end_date = line.end_date or today
                if end_date < line.start_date:
                    continue
                total_days += (end_date - line.start_date).days + 1
            employee.resonnocare_overall_experience_years = round(total_days / 365.0, 2)

    @api.constrains(
        "clinic_role",
        "attendance_profile",
        "clinic_id",
        "work_location_id",
        "resonnocare_profile",
    )
    def _check_resonnocare_profile_location_matrix(self):
        for employee in self:
            role = employee.clinic_role
            attendance_profile = employee.attendance_profile
            clinic_type = employee.clinic_id.clinic_type if employee.clinic_id else False
            billing_type = (
                employee.clinic_id._get_effective_billing_type()
                if employee.clinic_id and hasattr(employee.clinic_id, "_get_effective_billing_type")
                else False
            )
            has_any_location = bool(employee.clinic_id or employee.work_location_id)

            if attendance_profile == "fixed" and role in ("front_desk", "technician") and not has_any_location:
                raise UserError(
                    _("Fixed profile employees must have a Clinic or Work Location mapped.")
                )

            if role == "call_centre":
                if attendance_profile and attendance_profile != "fixed":
                    raise UserError(
                        _("Call Centre employees must use Fixed attendance profile.")
                    )
                if employee.clinic_id:
                    raise UserError(
                        _("Call Centre role must be mapped to Head Office/Work Location, not a clinic.")
                    )
                if not employee.work_location_id:
                    raise UserError(
                        _("Call Centre role must have a Work Location / Head Office mapped.")
                    )

            if attendance_profile == "roaming" and role in ("technician", "front_desk", "call_centre"):
                raise UserError(
                    _("Roaming profile is not allowed for this role in fixed-location setups.")
                )

            if not clinic_type:
                continue

            # Clinic mapping:
            # - Billing Sub Type B2B -> SIS behavior
            # - Billing Sub Type B2C -> Corporate behavior
            is_sis_clinic = billing_type == "b2b"
            is_corporate_clinic = billing_type == "b2c"

            if is_corporate_clinic or is_sis_clinic:
                if not employee.clinic_id:
                    raise UserError(
                        _("Clinic is mandatory when Location Type is Corporate Clinic or SIS Clinic.")
                    )
                if role == "call_centre":
                    raise UserError(
                        _("Call Centre role is not allowed for clinic location types.")
                    )
                is_audiologist_profile = employee.resonnocare_profile in (
                    "audiologist",
                    "audiologist_leave_support",
                )
                if (
                    attendance_profile
                    and attendance_profile != "fixed"
                    and role != "doctor"
                    and not is_audiologist_profile
                ):
                    raise UserError(
                        _(
                            "Only Doctor or Audiologist profile can use Roaming profile in clinic location types."
                        )
                    )
                # if is_sis_clinic and role == "technician":
                #     raise UserError(
                #         _("Technician role is not allowed for SIS Clinic as per profile-location matrix.")
                #     )

    @api.constrains("resonnocare_function", "clinic_id", "clinic_role")
    def _check_clinic_and_role_pairing(self):
        for employee in self:
            if employee.resonnocare_function in {"hr", "admin"}:
                continue
            if employee.clinic_role == "call_centre" and not employee.clinic_id:
                continue
            if bool(employee.clinic_id) != bool(employee.clinic_role):
                raise UserError(
                    _("Clinic and Clinic Role must be set together for non-HR/Admin employees.")
                )

    @api.constrains("resonnocare_profile", "attendance_profile")
    def _check_resonnocare_profile_attendance_alignment(self):
        fixed_profiles = {"back_office", "call_centre", "audiologist", "technician"}
        roaming_profiles = {"management", "audiologist_leave_support", "sales"}
        for employee in self:
            if not employee.resonnocare_profile or not employee.attendance_profile:
                continue
            if (
                employee.resonnocare_profile in fixed_profiles
                and employee.attendance_profile != "fixed"
            ):
                raise UserError(
                    _(
                        "Selected profile requires Fixed attendance profile as per client matrix."
                    )
                )
            if (
                employee.resonnocare_profile in roaming_profiles
                and employee.attendance_profile != "roaming"
            ):
                raise UserError(
                    _(
                        "Selected profile requires Roaming attendance profile as per client matrix."
                    )
                )

    def _get_published_handbook(self):
        return self.env["resonnocare.hr.handbook.version"].search(
            [("state", "=", "published")], limit=1
        )

    def _has_running_contract(self):
        self.ensure_one()
        if "hr.contract" not in self.env or not self.id:
            return False
        employee = self.sudo()

        # Prefer Odoo's own current contract pointer when available.
        if "contract_id" in employee._fields and employee.contract_id:
            current = employee.contract_id.sudo()
            if current.state == "open":
                return True

        contract_model = self.env["hr.contract"].sudo()
        domain = [("state", "=", "open"), ("employee_id", "=", self.id)]
        if employee.user_id:
            domain = [
                ("state", "=", "open"),
                "|",
                ("employee_id", "=", self.id),
                ("employee_id.user_id", "=", employee.user_id.id),
            ]
        if "active" in contract_model._fields:
            has_contract = bool(contract_model.with_context(active_test=False).search_count(domain))
        else:
            has_contract = bool(contract_model.search_count(domain))
        if has_contract:
            return True

        # Fallback for duplicate/misaligned employee links: match by generated Employee ID.
        if employee.resonnocare_employee_code:
            code_domain = [
                ("state", "=", "open"),
                ("employee_id.resonnocare_employee_code", "=", employee.resonnocare_employee_code),
            ]
            if "active" in contract_model._fields:
                has_by_code = bool(contract_model.with_context(active_test=False).search_count(code_domain))
            else:
                has_by_code = bool(contract_model.search_count(code_domain))
            if has_by_code:
                return True

        # Last-resort fallback for legacy data mismatch: same employee name (+company when available).
        if employee.name:
            name_domain = [("state", "=", "open"), ("employee_id.name", "=", employee.name)]
            if employee.company_id:
                name_domain.append(("employee_id.company_id", "=", employee.company_id.id))
            if "active" in contract_model._fields:
                return bool(contract_model.with_context(active_test=False).search_count(name_domain))
            return bool(contract_model.search_count(name_domain))

        return False

    def _compute_onboarding_compliance(self):
        handbook = self._get_published_handbook()
        acceptance_model = self.env["resonnocare.hr.handbook.acceptance"]
        contract_model = self.env["hr.contract"] if "hr.contract" in self.env else False

        for employee in self:
            acceptance = False
            if handbook and employee.id:
                acceptance = acceptance_model.search(
                    [
                        ("employee_id", "=", employee.id),
                        ("handbook_version_id", "=", handbook.id),
                    ],
                    limit=1,
                )
            has_contract = employee._has_running_contract() if contract_model else False

            employee.onboarding_handbook_accepted = bool(acceptance)
            employee.onboarding_handbook_accepted_on = (
                acceptance.accepted_on if acceptance else False
            )
            employee.onboarding_handbook_ip = (
                acceptance.accepted_ip if acceptance else False
            )
            missing_fields = employee._get_profile_missing_fields()
            employee.onboarding_profile_complete = not missing_fields
            employee.onboarding_profile_missing_fields = ", ".join(missing_fields)
            if handbook and not acceptance:
                employee.onboarding_status = "pending_handbook"
            elif contract_model and not has_contract:
                employee.onboarding_status = "pending_contract"
            elif missing_fields:
                employee.onboarding_status = "pending_profile"
            else:
                employee.onboarding_status = "completed"

    def _compute_onboarding_contract_status(self):
        for employee in self:
            has_contract = employee._has_running_contract()
            employee.onboarding_contract_ready = has_contract
            employee.onboarding_contract_status = "running" if has_contract else "not_running"

    def _is_hr_onboarding_actor(self):
        user = self.env.user
        return user.has_group("resonnocare_base.group_resonnocare_hr") or user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        )

    def _get_activity_type(self):
        return self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)

    def _schedule_employee_activity_if_missing(self, user, summary, note):
        self.ensure_one()
        if not user:
            return False
        activity_type = self._get_activity_type()
        if not activity_type:
            return False
        existing = self.env["mail.activity"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("user_id", "=", user.id),
                ("summary", "=", summary),
                ("activity_type_id", "=", activity_type.id),
            ],
            limit=1,
        )
        if existing:
            return False
        self.activity_schedule(
            activity_type_id=activity_type.id,
            user_id=user.id,
            summary=summary,
            note=note,
            date_deadline=fields.Date.today() + timedelta(days=2),
        )
        return True

    def _find_user_by_group_xmlids(self, xmlids):
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if not group:
                continue
            user = self.env["res.users"].search(
                [("groups_id", "in", group.id), ("share", "=", False)],
                limit=1,
            )
            if user:
                return user
        return self.env["res.users"]

    def _get_joining_stage_activity_summaries(self):
        return [
            _("Prepare onboarding plan"),
            _("Arrange workstation and ID card"),
            _("Confirm payroll activation"),
            _("Provision system access and laptop"),
        ]

    def _run_post_joining_sync(self):
        """
        Run optional system-sync hooks after joining activation and log outcomes.
        Concrete integrations can override/extend by implementing the hook names.
        """
        self.ensure_one()
        sync_steps = [
            (_("Payroll"), "_resonnocare_sync_payroll"),
            (_("Attendance/Leave"), "_resonnocare_sync_attendance_leave"),
            (_("IT Provisioning"), "_resonnocare_sync_it_provisioning"),
            (_("Admin/Facilities"), "_resonnocare_sync_admin_facilities"),
            (_("Compliance"), "_resonnocare_sync_compliance"),
        ]
        lines = []
        for label, method_name in sync_steps:
            method = getattr(self, method_name, None)
            if callable(method):
                try:
                    method()
                    status = _("Automated sync completed")
                except Exception as exc:  # pragma: no cover
                    _logger.exception("Post-joining sync failed for %s (%s)", self.name, method_name)
                    status = _("Sync failed: %s") % str(exc)
            else:
                status = _("Automation hook not configured; manual follow-up required")
            lines.append("%s: %s" % (label, status))

        self.message_post(
            subject=_("Post-Activation Sync Status"),
            body="<br/>".join(lines),
        )

    def _resonnocare_sync_payroll(self):
        self.ensure_one()
        manager_user = self._find_user_by_group_xmlids(
            [
                "hr_payroll.group_hr_payroll_manager",
                "hr_payroll.group_hr_payroll_user",
                "resonnocare_base.group_resonnocare_hr",
            ]
        )
        missing = []
        if "hr.contract" in self.env:
            contract = self.env["hr.contract"].sudo().search(
                [("employee_id", "=", self.id), ("state", "=", "open")],
                order="date_start desc, id desc",
                limit=1,
            )
            if not contract:
                missing.append(_("Running Contract"))
            else:
                if "struct_id" in contract._fields and not contract.struct_id:
                    missing.append(_("Salary Structure on Contract"))
                if "schedule_pay" in contract._fields and not contract.schedule_pay:
                    missing.append(_("Scheduled Pay on Contract"))
        else:
            missing.append(_("Payroll module"))

        if missing:
            self._schedule_employee_activity_if_missing(
                manager_user,
                _("Complete payroll readiness"),
                _(
                    "Payroll sync check failed for %(employee)s. Missing: %(missing)s",
                    employee=self.name,
                    missing=", ".join(missing),
                ),
            )
            return False
        return True

    def _resonnocare_sync_attendance_leave(self):
        self.ensure_one()
        hr_user = self._find_user_by_group_xmlids(
            [
                "resonnocare_base.group_resonnocare_hr",
                "resonnocare_base.group_resonnocare_super_admin",
            ]
        )
        missing = []
        if not self.attendance_profile:
            missing.append(_("Attendance Profile"))
        if not self.resonnocare_weekly_off_pattern:
            missing.append(_("Weekly Off Pattern"))
        if not self.resource_calendar_id:
            missing.append(_("Shift / Working Schedule"))

        if missing:
            self._schedule_employee_activity_if_missing(
                hr_user,
                _("Complete attendance/leave mapping"),
                _(
                    "Attendance/Leave sync check failed for %(employee)s. Missing: %(missing)s",
                    employee=self.name,
                    missing=", ".join(missing),
                ),
            )
            return False
        return True

    def _resonnocare_sync_it_provisioning(self):
        self.ensure_one()
        it_user = self._find_user_by_group_xmlids(
            ["base.group_system", "resonnocare_base.group_resonnocare_super_admin"]
        )
        self._schedule_employee_activity_if_missing(
            it_user,
            _("IT provisioning confirmation"),
            _(
                "Confirm email, app access, and endpoint provisioning for %(employee)s.",
                employee=self.name,
            ),
        )
        return True

    def _resonnocare_sync_admin_facilities(self):
        self.ensure_one()
        admin_user = self._find_user_by_group_xmlids(
            [
                "resonnocare_base.group_clinic_admin",
                "resonnocare_base.group_resonnocare_super_admin",
            ]
        )
        self._schedule_employee_activity_if_missing(
            admin_user,
            _("Admin/facilities confirmation"),
            _(
                "Confirm workstation, ID, and facility readiness for %(employee)s.",
                employee=self.name,
            ),
        )
        return True

    def _resonnocare_sync_compliance(self):
        self.ensure_one()
        hr_user = self._find_user_by_group_xmlids(
            [
                "resonnocare_base.group_resonnocare_hr",
                "resonnocare_base.group_resonnocare_super_admin",
            ]
        )
        self._schedule_employee_activity_if_missing(
            hr_user,
            _("Compliance confirmation"),
            _(
                "Confirm handbook/legal/compliance documentation is complete for %(employee)s.",
                employee=self.name,
            ),
        )
        return True

    def _ensure_resonnocare_uat_checklist(self):
        self.ensure_one()
        checklist_model = self.env["resonnocare.uat.checklist"].sudo()
        templates = [
            (10, "onboarding", _("Onboarding flow validated")),
            (20, "attendance", _("Attendance + regularization flow validated")),
            (30, "leave", _("Leave workflow validated")),
            (40, "payroll", _("Payroll impact validated")),
            (50, "integration", _("IT/Admin/Compliance sync validated")),
        ]
        owner = (
            self.leave_manager_id.user_id
            or self.parent_id.user_id
            or self._find_user_by_group_xmlids(
                [
                    "resonnocare_base.group_resonnocare_hr",
                    "resonnocare_base.group_resonnocare_super_admin",
                ]
            )
        )
        for sequence, area, name in templates:
            exists = checklist_model.search_count(
                [("employee_id", "=", self.id), ("name", "=", name)]
            )
            if exists:
                continue
            checklist_model.create(
                {
                    "employee_id": self.id,
                    "sequence": sequence,
                    "area": area,
                    "name": name,
                    "owner_user_id": owner.id if owner else False,
                }
            )
        return True

    def _joining_sla_token(self, activity, level):
        return "[JOINING_SLA][ACT:%s][%s]" % (activity.id, level)

    def _has_joining_sla_notification(self, activity, level):
        token = self._joining_sla_token(activity, level)
        return bool(
            self.env["mail.message"].sudo().search_count(
                [
                    ("model", "=", self._name),
                    ("res_id", "=", activity.res_id),
                    ("body", "ilike", token),
                ]
            )
        )

    def _post_joining_sla_notification(self, activity, level):
        employee = self.browse(activity.res_id)
        if not employee.exists():
            return

        token = self._joining_sla_token(activity, level)
        if level == "24H":
            subject = _("Joining Activity Reminder (24h)")
            message = _(
                "%(token)s Pending joining activity for %(employee)s: %(summary)s. Please action this within SLA.",
                token=token,
                employee=employee.name,
                summary=activity.summary,
            )
            partner_ids = [activity.user_id.partner_id.id] if activity.user_id.partner_id else []
        else:
            subject = _("Joining Activity Escalation (48h)")
            message = _(
                "%(token)s Escalation: joining activity pending beyond 48h for %(employee)s: %(summary)s.",
                token=token,
                employee=employee.name,
                summary=activity.summary,
            )
            partner_ids = []
            if activity.user_id.partner_id:
                partner_ids.append(activity.user_id.partner_id.id)
            manager_user = employee.functional_manager_id.user_id
            if manager_user and manager_user.partner_id:
                partner_ids.append(manager_user.partner_id.id)
            hr_group = self.env.ref("resonnocare_base.group_resonnocare_hr", raise_if_not_found=False)
            if hr_group:
                partner_ids.extend(hr_group.users.mapped("partner_id").ids)
            partner_ids = list(set(partner_ids))

        employee.message_post(
            body=message,
            subject=subject,
            partner_ids=partner_ids,
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )

    @api.model
    def cron_joining_stage_activity_sla(self):
        summaries = self._get_joining_stage_activity_summaries()
        activities = self.env["mail.activity"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("summary", "in", summaries),
            ]
        )
        now = fields.Datetime.now()
        for activity in activities:
            create_date = activity.create_date or now
            age = now - create_date
            if age >= timedelta(hours=48):
                if not self._has_joining_sla_notification(activity, "48H"):
                    self._post_joining_sla_notification(activity, "48H")
            elif age >= timedelta(hours=24):
                if not self._has_joining_sla_notification(activity, "24H"):
                    self._post_joining_sla_notification(activity, "24H")
        return True

    def _assign_resonnocare_employee_code(self):
        for employee in self:
            if employee.resonnocare_employee_code:
                continue
            code = self.env["ir.sequence"].sudo().next_by_code(
                "resonnocare.hr.employee.code"
            )
            if code:
                employee.sudo().write({"resonnocare_employee_code": code})

    def action_initiate_joining_stage(self):
        if not self._is_hr_onboarding_actor():
            raise AccessError(_("Only HR can initiate joining stage."))

        now = fields.Datetime.now()
        for employee in self:
            employee._auto_assign_holiday_calendar_mapping()
            employee._compute_onboarding_compliance()
            missing_setup_fields = employee._get_hris_setup_missing_fields()
            if missing_setup_fields:
                raise UserError(
                    _(
                        "Complete HRIS setup before initiating joining stage for %(employee)s. Missing: %(fields)s",
                        employee=employee.name,
                        fields=", ".join(missing_setup_fields),
                    )
                )
            if employee.onboarding_status != "completed":
                raise UserError(
                    _(
                        "Cannot initiate joining stage until onboarding is completed for %(employee)s. Current status: %(status)s",
                        employee=employee.name,
                        status=employee.onboarding_status or _("unknown"),
                    )
                )
            if employee.onboarding_joining_stage_state != "not_started":
                raise UserError(
                    _(
                        "Joining stage is already started for %(employee)s.",
                        employee=employee.name,
                    )
                )

            employee._assign_resonnocare_employee_code()

            employee.write(
                {
                    "onboarding_joining_stage_state": "initiated",
                    "onboarding_joining_stage_initiated_by": self.env.user.id,
                    "onboarding_joining_stage_initiated_on": now,
                }
            )

            manager_user = employee.parent_id.user_id or employee.leave_manager_id.user_id
            admin_user = self._find_user_by_group_xmlids(
                [
                    "resonnocare_base.group_clinic_admin",
                    "resonnocare_base.group_resonnocare_super_admin",
                ]
            )
            payroll_user = self._find_user_by_group_xmlids(
                [
                    "hr_payroll.group_hr_payroll_user",
                    "hr_payroll.group_hr_payroll_manager",
                    "resonnocare_base.group_resonnocare_hr",
                ]
            )
            it_user = self._find_user_by_group_xmlids(
                [
                    "base.group_system",
                    "resonnocare_base.group_resonnocare_super_admin",
                ]
            )

            self._schedule_employee_activity_if_missing(
                manager_user,
                _("Prepare onboarding plan"),
                _("Prepare Day-1 onboarding plan and first-week ramp-up tasks."),
            )
            self._schedule_employee_activity_if_missing(
                admin_user,
                _("Arrange workstation and ID card"),
                _("Please arrange workstation, ID card, and facilities readiness."),
            )
            self._schedule_employee_activity_if_missing(
                payroll_user,
                _("Confirm payroll activation"),
                _("Please verify payroll setup and salary-cycle readiness."),
            )
            self._schedule_employee_activity_if_missing(
                it_user,
                _("Provision system access and laptop"),
                _("Please provision user access, email, and IT assets."),
            )

            employee.message_post(
                body=_(
                    "Joining stage initiated. Activities created for Manager, Admin, Payroll, and IT."
                )
            )
        return True

    def action_mark_joining_activated(self):
        if not self._is_hr_onboarding_actor():
            raise AccessError(_("Only HR can mark joining stage as activated."))

        activity_type = self._get_activity_type()
        summaries = self._get_joining_stage_activity_summaries()
        now = fields.Datetime.now()

        for employee in self:
            if employee.onboarding_joining_stage_state != "initiated":
                raise UserError(
                    _(
                        "Joining stage can be activated only from Initiated state for %(employee)s.",
                        employee=employee.name,
                    )
                )

            domain = [
                ("res_model", "=", self._name),
                ("res_id", "=", employee.id),
                ("summary", "in", summaries),
            ]
            if activity_type:
                domain.append(("activity_type_id", "=", activity_type.id))
            pending_activities = self.env["mail.activity"].search(domain)
            if pending_activities:
                pending_details = ", ".join(
                    sorted(
                        {
                            "%s (%s)"
                            % (activity.summary, activity.user_id.name or _("Unassigned"))
                            for activity in pending_activities
                        }
                    )
                )
                raise UserError(
                    _(
                        "Cannot activate joining stage while onboarding activities are still pending for %(employee)s: %(activities)s",
                        employee=employee.name,
                        activities=pending_details,
                    )
                )

            employee.write(
                {
                    "onboarding_joining_stage_state": "activated",
                    "onboarding_joining_stage_activated_by": self.env.user.id,
                    "onboarding_joining_stage_activated_on": now,
                    "onboarding_attendance_ready": True,
                    "onboarding_attendance_ready_by": self.env.user.id,
                    "onboarding_attendance_ready_on": now,
                }
            )
            employee._run_post_joining_sync()
            employee._ensure_resonnocare_uat_checklist()
            employee.message_post(
                body=_("Joining stage activated. Attendance is marked ready.")
            )
        return True

    def _sync_handbook_home_action(self):
        handbook_action = self.env.ref(
            "resonnocare_hr.action_hr_handbook_accept_wizard", raise_if_not_found=False
        )
        profile_action = self.env.ref(
            "resonnocare_hr.action_open_resonnocare_my_profile_server", raise_if_not_found=False
        )
        crm_action = self.env.ref(
            "resonnocare_crm.action_resonnocare_crm_my_leads", raise_if_not_found=False
        )
        if not handbook_action:
            return
        handbook = self._get_published_handbook()
        acceptance_model = self.env["resonnocare.hr.handbook.acceptance"]
        contract_model = self.env["hr.contract"] if "hr.contract" in self.env else False

        for employee in self:
            user = employee.user_id.sudo()
            if not user:
                continue
            # Never force onboarding home-action for system/super-admin users.
            if user.has_group("base.group_system") or user.has_group(
                "resonnocare_base.group_resonnocare_super_admin"
            ):
                if user.action_id and user.action_id.id in (
                    handbook_action.id,
                    profile_action.id if profile_action else 0,
                ):
                    user.write({"action_id": False})
                continue
            has_accepted = bool(
                handbook
                and acceptance_model.search_count(
                    [
                        ("employee_id", "=", employee.id),
                        ("handbook_version_id", "=", handbook.id),
                    ]
                )
            )
            has_contract = employee._has_running_contract() if contract_model else True

            target_action_id = False
            if handbook and (not has_accepted or not has_contract):
                target_action_id = handbook_action.id
            elif user.has_group("resonnocare_base.group_crm") and crm_action:
                target_action_id = crm_action.id
            elif employee.onboarding_status == "pending_profile" and profile_action:
                target_action_id = profile_action.id

            if target_action_id:
                if user.action_id.id != target_action_id:
                    user.write({"action_id": target_action_id})
            elif user.action_id and user.action_id.id in (
                handbook_action.id,
                profile_action.id if profile_action else 0,
            ):
                user.write({"action_id": False})

    def _sync_user_role_from_employee(self):
        """Keep user role groups and assigned clinic in sync with HR employee."""
        managed_group_ids = []
        for xmlid in set(self._ROLE_TO_GROUP_XMLID.values()):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                managed_group_ids.append(group.id)
        leave_user_group = self.env.ref("hr_holidays.group_hr_holidays_user", raise_if_not_found=False)
        leave_manager_group = self.env.ref("hr_holidays.group_hr_holidays_manager", raise_if_not_found=False)
        payroll_user_group = self.env.ref("payroll.group_payroll_user", raise_if_not_found=False)
        payroll_manager_group = self.env.ref("payroll.group_payroll_manager", raise_if_not_found=False)
        sales_user_group = self.env.ref("sales_team.group_sale_salesman", raise_if_not_found=False)
        sales_all_docs_group = self.env.ref(
            "sales_team.group_sale_salesman_all_leads", raise_if_not_found=False
        )
        sales_manager_group = self.env.ref("sales_team.group_sale_manager", raise_if_not_found=False)
        account_invoice_group = self.env.ref(
            "account.group_account_invoice", raise_if_not_found=False
        )
        stock_user_group = self.env.ref("stock.group_stock_user", raise_if_not_found=False)
        purchase_user_group = self.env.ref(
            "purchase.group_purchase_user", raise_if_not_found=False
        )
        administration_access_rights_group = self.env.ref(
            "base.group_erp_manager", raise_if_not_found=False
        )
        doctor_group = self.env.ref("resonnocare_base.group_doctor", raise_if_not_found=False)
        front_desk_group = self.env.ref(
            "resonnocare_base.group_front_desk", raise_if_not_found=False
        )
        external_doctor_group = self.env.ref(
            "resonnocare_base.group_external_doctor", raise_if_not_found=False
        )

        for employee in self:
            user = employee.user_id.sudo()
            if not user:
                continue

            group_commands = [(3, group_id) for group_id in managed_group_ids]
            role_group_xmlid = self._ROLE_TO_GROUP_XMLID.get(employee.clinic_role)
            if role_group_xmlid:
                role_group = self.env.ref(role_group_xmlid, raise_if_not_found=False)
                if role_group:
                    group_commands.append((4, role_group.id))
            if employee.clinic_role == "technician" and front_desk_group:
                # Technician should have full Front Desk access as per client request.
                group_commands.append((4, front_desk_group.id))

            # Time Off access normalization:
            # - HR/super-admin keep their existing access
            # - Only real team managers get manager queue access
            # - Normal employees get no leave-management group
            if not (
                user.has_group("resonnocare_base.group_resonnocare_hr")
                or user.has_group("resonnocare_base.group_resonnocare_super_admin")
            ):
                if external_doctor_group:
                    group_commands.append((3, external_doctor_group.id))
                if employee.clinic_role != "doctor" and doctor_group:
                    group_commands.append((3, doctor_group.id))
                has_team = bool(
                    self.sudo().search_count(
                        [
                            ("id", "!=", employee.id),
                            ("active", "=", True),
                            "|",
                            ("parent_id", "=", employee.id),
                            ("leave_manager_id", "=", employee.id),
                        ]
                    )
                )
                if leave_user_group:
                    group_commands.append((3, leave_user_group.id))
                if leave_manager_group:
                    group_commands.append((3, leave_manager_group.id))
                if has_team and leave_user_group:
                    group_commands.append((4, leave_user_group.id))
                # Prevent employee users from getting payroll management visibility.
                if payroll_user_group:
                    group_commands.append((3, payroll_user_group.id))
                if payroll_manager_group:
                    group_commands.append((3, payroll_manager_group.id))
                if employee.clinic_role in ("front_desk", "technician"):
                    if sales_user_group:
                        group_commands.append((4, sales_user_group.id))
                    if sales_all_docs_group:
                        group_commands.append((3, sales_all_docs_group.id))
                    if sales_manager_group:
                        group_commands.append((3, sales_manager_group.id))
                    if account_invoice_group:
                        group_commands.append((4, account_invoice_group.id))
                    if stock_user_group:
                        group_commands.append((4, stock_user_group.id))
                    if purchase_user_group:
                        group_commands.append((4, purchase_user_group.id))
                    if administration_access_rights_group:
                        group_commands.append((4, administration_access_rights_group.id))
                elif employee.clinic_role == "call_centre":
                    if administration_access_rights_group:
                        group_commands.append((4, administration_access_rights_group.id))
                elif employee.clinic_role != "call_centre":
                    if sales_user_group:
                        group_commands.append((3, sales_user_group.id))
                    if sales_all_docs_group:
                        group_commands.append((3, sales_all_docs_group.id))
                    if sales_manager_group:
                        group_commands.append((3, sales_manager_group.id))
                    if administration_access_rights_group:
                        group_commands.append((3, administration_access_rights_group.id))
            else:
                # HR/Super Admin keep payroll groups for payroll operations.
                if payroll_user_group:
                    group_commands.append((4, payroll_user_group.id))
                if payroll_manager_group:
                    group_commands.append((4, payroll_manager_group.id))

            write_vals = {"groups_id": group_commands}
            if "clinic_id" in user._fields:
                write_vals["clinic_id"] = employee.clinic_id.id or False
            user.write(write_vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("clinic_role") == "call_centre":
                vals["clinic_id"] = False
        employees = super().create(vals_list)
        employees.filtered(lambda e: e.resonnocare_function in {"hr", "admin"}).sudo().write(
            {"clinic_id": False, "clinic_role": False}
        )
        employees._auto_assign_holiday_calendar_mapping()
        employees._sync_user_role_from_employee()
        employees._sync_handbook_home_action()
        return employees

    def write(self, vals):
        # Employees can maintain personal info but must not alter HR-owned setup fields.
        if not self.env.user.has_group(
            "resonnocare_base.group_resonnocare_hr"
        ) and not self.env.user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        ):
            blocked = self._SELF_SERVICE_BLOCKED_FIELDS.intersection(vals.keys())
            if blocked:
                raise AccessError(
                    _("You cannot modify HR-managed fields: %s. Please contact HR.")
                    % ", ".join(sorted(blocked))
                )

        # Persist mapping-backed fields explicitly to avoid UI-cache/inverse edge cases.
        mapping_field_map = {
            "resonnocare_function": "function_name",
            "resonnocare_region_id": "region_id",
            "resonnocare_weekly_off_pattern": "weekly_off_pattern",
            "resonnocare_holiday_calendar_id": "holiday_calendar_id",
        }
        incoming_mapping_vals = {
            target: vals[source]
            for source, target in mapping_field_map.items()
            if source in vals
        }

        if vals.get("resonnocare_function") in {"hr", "admin"}:
            vals = dict(vals)
            vals["clinic_id"] = False
            vals["clinic_role"] = False
        elif vals.get("clinic_role") == "call_centre":
            vals = dict(vals)
            vals["clinic_id"] = False

        result = super().write(vals)

        if incoming_mapping_vals and self._resonnocare_master_mapping_table_exists():
            for employee in self:
                mapping = employee.sudo()._get_or_create_master_mapping()
                mapping.sudo().write(incoming_mapping_vals)

        if any(
            key in vals
            for key in ("clinic_id", "resonnocare_state_id", "resonnocare_region_id", "resonnocare_country_id")
        ):
            self._auto_assign_holiday_calendar_mapping()
        if any(key in vals for key in ("clinic_role", "user_id", "clinic_id")):
            self._sync_user_role_from_employee()
        self._sync_handbook_home_action()
        return result
