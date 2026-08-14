import calendar
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrLeave(models.Model):
    _inherit = "hr.leave"

    resonnocare_holiday_calendar_id = fields.Many2one(
        "resonnocare.holiday.calendar",
        string="Holiday Calendar",
        index=True,
        copy=False,
        readonly=True,
    )
    resonnocare_is_calendar_holiday = fields.Boolean(
        string="Calendar Holiday",
        default=False,
        index=True,
        copy=False,
        readonly=True,
    )

    resonnocare_submitted_on = fields.Datetime(readonly=True, copy=False)
    resonnocare_reminder_24_sent = fields.Boolean(default=False, readonly=True, copy=False)
    resonnocare_escalation_48_sent = fields.Boolean(default=False, readonly=True, copy=False)
    resonnocare_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        related="employee_id.clinic_id",
        store=True,
        readonly=True,
    )
    resonnocare_region_id = fields.Many2one(
        "res.country.group",
        string="Region",
        compute="_compute_resonnocare_region_id",
        store=True,
        readonly=True,
    )

    resonnocare_cancel_request_state = fields.Selection(
        [
            ("none", "No Request"),
            ("requested", "Manager Approval Requested"),
            ("approved", "Cancellation Approved"),
            ("rejected", "Cancellation Rejected"),
        ],
        default="none",
        copy=False,
        tracking=True,
    )
    resonnocare_cancel_request_reason = fields.Text(copy=False)
    resonnocare_cancel_requested_by = fields.Many2one("res.users", readonly=True, copy=False)
    resonnocare_cancel_requested_on = fields.Datetime(readonly=True, copy=False)
    resonnocare_cancel_decided_by = fields.Many2one("res.users", readonly=True, copy=False)
    resonnocare_cancel_decided_on = fields.Datetime(readonly=True, copy=False)

    @api.depends("employee_id", "employee_id.clinic_id", "employee_id.clinic_id.country_id")
    def _compute_resonnocare_region_id(self):
        country_group_model = self.env["res.country.group"]
        for leave in self:
            country = leave.employee_id.clinic_id.country_id
            leave.resonnocare_region_id = (
                country_group_model.search([("country_ids", "in", country.id)], limit=1)
                if country
                else False
            )

    def _is_hr_actor(self):
        user = self.env.user
        return (
            user.has_group("hr_holidays.group_hr_holidays_user")
            or user.has_group("hr_holidays.group_hr_holidays_manager")
            or user.has_group("resonnocare_base.group_resonnocare_hr")
            or user.has_group("resonnocare_base.group_resonnocare_super_admin")
        )

    def _get_leave_manager_user(self):
        self.ensure_one()
        employee = self.employee_id
        return employee.leave_manager_id.user_id or employee.parent_id.user_id

    def _is_leave_manager_actor(self):
        self.ensure_one()
        manager_user = self._get_leave_manager_user()
        return bool(manager_user and manager_user.id == self.env.user.id)

    def _is_self_leave_request(self):
        self.ensure_one()
        return bool(self.employee_id and self.employee_id.user_id and self.employee_id.user_id == self.env.user)

    def _is_backdated_request(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return bool(self.request_date_from and self.request_date_from < today)

    def _check_request_window(self):
        if self.env.context.get("resonnocare_holiday_sync"):
            return
        today = fields.Date.context_today(self)
        for leave in self:
            if leave.resonnocare_is_calendar_holiday:
                continue
            if not leave.request_date_from or not leave.request_date_to:
                continue

            if leave.request_date_from.year != today.year or leave.request_date_to.year != today.year:
                raise ValidationError(
                    _("Leave dates must fall within the current calendar year.")
                )

            if leave.request_date_from < today:
                days_back = (today - leave.request_date_from).days
                if days_back > 30:
                    raise ValidationError(
                        _("Backdated leave is only allowed up to 30 days.")
                    )

            if leave.request_date_from > today:
                days_ahead = (leave.request_date_from - today).days
                if days_ahead > 365:
                    raise ValidationError(
                        _("Future leave is only allowed up to 365 days.")
                    )

    @api.depends("state", "employee_id", "department_id")
    def _compute_can_approve(self):
        super()._compute_can_approve()
        for leave in self:
            if leave._is_self_leave_request():
                leave.can_approve = False

    def _salary_processed_for_leave(self):
        self.ensure_one()
        if "hr.payslip" not in self.env:
            return False

        payslip_model = self.env["hr.payslip"].sudo()
        if "state" not in payslip_model._fields:
            return False

        processed_states = ["done"]
        state_selection = payslip_model._fields["state"].selection
        if callable(state_selection):
            state_selection = state_selection(payslip_model)
        state_keys = {
            item[0]
            for item in (state_selection or [])
            if isinstance(item, (tuple, list)) and item
        }
        if "paid" in state_keys:
            processed_states.append("paid")

        return bool(
            payslip_model.search_count(
                [
                    ("employee_id", "=", self.employee_id.id),
                    ("date_from", "<=", self.request_date_to),
                    ("date_to", ">=", self.request_date_from),
                    ("state", "in", processed_states),
                ]
            )
        )

    def _get_activity_type(self):
        return self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)

    def _notify_partners(self, partners, subject, body):
        self.ensure_one()
        partners = partners.filtered(lambda p: p)
        if not partners:
            return
        mail_server = self.env["ir.mail_server"].sudo().search(
            [("active", "=", True), ("smtp_host", "!=", False)],
            limit=1,
        )
        if mail_server:
            self.message_notify(
                partner_ids=partners.ids,
                subject=subject,
                body=body,
                email_layout_xmlid="mail.mail_notification_light",
            )
            return
        self.message_post(
            subject=subject,
            body=body,
            partner_ids=partners.ids,
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )

    def _notify_leave_applied(self):
        self.ensure_one()
        manager_user = self._get_leave_manager_user()
        partners = self.env["res.partner"]
        if manager_user and manager_user.partner_id:
            partners |= manager_user.partner_id
        functional_manager_user = self.employee_id.functional_manager_id.user_id
        if functional_manager_user and functional_manager_user.partner_id:
            partners |= functional_manager_user.partner_id
        self._notify_partners(
            partners,
            _("Leave Applied: Approval Required"),
            _(
                "Leave request %(leave)s for %(employee)s has been submitted and requires your approval.",
                leave=self.display_name,
                employee=self.employee_id.name,
            ),
        )

    def _notify_leave_approved(self):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        self._notify_partners(
            employee_partner,
            _("Leave Approved"),
            _(
                "Your leave request %(leave)s has been approved.",
                leave=self.display_name,
            ),
        )

    def _notify_leave_declined(self):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        self._notify_partners(
            employee_partner,
            _("Leave Declined"),
            _(
                "Your leave request %(leave)s has been declined.",
                leave=self.display_name,
            ),
        )

    def _notify_cancellation_requested(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        manager_user = self._get_leave_manager_user()
        if manager_user and manager_user.partner_id:
            partners |= manager_user.partner_id
        if self.employee_id.functional_manager_id.user_id.partner_id:
            partners |= self.employee_id.functional_manager_id.user_id.partner_id
        self._notify_partners(
            partners,
            _("Leave Cancellation Requested"),
            _(
                "Cancellation requested for leave %(leave)s of %(employee)s.",
                leave=self.display_name,
                employee=self.employee_id.name,
            ),
        )

    def _notify_cancellation_decision(self, approved):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        if approved:
            subject = _("Leave Cancellation Approved")
            body = _(
                "Your leave cancellation request for %(leave)s has been approved.",
                leave=self.display_name,
            )
        else:
            subject = _("Leave Cancellation Rejected")
            body = _(
                "Your leave cancellation request for %(leave)s has been rejected.",
                leave=self.display_name,
            )
        self._notify_partners(employee_partner, subject, body)

    def _schedule_activity_if_missing(self, user, summary):
        self.ensure_one()
        if not user:
            return
        activity_type = self._get_activity_type()
        if not activity_type:
            return

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
            return

        self.activity_schedule(
            activity_type_id=activity_type.id,
            user_id=user.id,
            summary=summary,
            note=_("Time off request requires your action."),
            date_deadline=fields.Date.today(),
        )

    def _schedule_manager_activity(self):
        self.ensure_one()
        manager_user = self._get_leave_manager_user()
        if manager_user:
            self._schedule_activity_if_missing(manager_user, _("Time off pending manager approval"))

    def _schedule_hr_activity(self):
        self.ensure_one()
        hr_user = self.env["res.users"].search(
            [
                "|",
                ("groups_id", "in", self.env.ref("resonnocare_base.group_resonnocare_hr").id),
                ("groups_id", "in", self.env.ref("resonnocare_base.group_resonnocare_super_admin").id),
            ],
            limit=1,
        )
        if hr_user:
            self._schedule_activity_if_missing(hr_user, _("Backdated leave pending HR approval"))

    @api.constrains("request_date_from", "request_date_to")
    def _constrain_resonnocare_leave_window(self):
        self._check_request_window()

    def _is_resonnocare_compoff_type(self):
        self.ensure_one()
        leave_type = self.holiday_status_id
        if not leave_type:
            return False
        type_name = (leave_type.name or "").strip().lower()
        return any(token in type_name for token in ("comp", "comp-off", "comp off", "compoff"))

    @api.constrains(
        "holiday_status_id",
        "request_unit_half",
        "request_unit_hours",
        "number_of_days",
        "number_of_days_display",
    )
    def _constrain_resonnocare_compoff_full_day(self):
        for leave in self:
            if not leave._is_resonnocare_compoff_type():
                continue

            if "request_unit_half" in leave._fields and leave.request_unit_half:
                raise ValidationError(_("Comp-Off can be applied only as full day."))
            if "request_unit_hours" in leave._fields and leave.request_unit_hours:
                raise ValidationError(_("Comp-Off can be applied only as full day."))

            days_value = False
            if "number_of_days_display" in leave._fields and leave.number_of_days_display:
                days_value = leave.number_of_days_display
            elif "number_of_days" in leave._fields and leave.number_of_days:
                days_value = leave.number_of_days

            if days_value not in (False, None):
                if abs(days_value - round(days_value)) > 1e-6:
                    raise ValidationError(_("Comp-Off can be applied only in full-day units."))

    def _post_create_resonnocare_submission_flow(self, records):
        now = fields.Datetime.now()
        for leave in records:
            if leave.state == "confirm" and not leave.resonnocare_submitted_on:
                leave.write(
                    {
                        "resonnocare_submitted_on": now,
                        "resonnocare_reminder_24_sent": False,
                        "resonnocare_escalation_48_sent": False,
                    }
                )
                leave._notify_leave_applied()
                leave._schedule_manager_activity()

    @api.model_create_multi
    def create(self, vals_list):
        try:
            records = super().create(vals_list)
        except ValidationError as err:
            if not self._resonnocare_allocation_error(err):
                raise
            retry_vals, switched = self._resonnocare_with_lwp_vals(vals_list)
            if not switched:
                raise
            records = super().create(retry_vals)
        self._post_create_resonnocare_submission_flow(records)
        return records

    def write(self, vals):
        try:
            result = super().write(vals)
        except ValidationError as err:
            if not self._resonnocare_allocation_error(err):
                raise
            pl_type = self._get_resonnocare_paid_leave_type()
            lwp_type = self._get_resonnocare_lwp_leave_type()
            if not (pl_type and lwp_type):
                raise
            retry_vals = dict(vals)
            if retry_vals.get("holiday_status_id") != pl_type.id:
                raise
            retry_vals["holiday_status_id"] = lwp_type.id
            result = super().write(retry_vals)

        if "state" in vals and vals["state"] == "confirm":
            now = fields.Datetime.now()
            for leave in self.filtered(lambda l: not l.resonnocare_submitted_on):
                leave.write(
                    {
                        "resonnocare_submitted_on": now,
                        "resonnocare_reminder_24_sent": False,
                        "resonnocare_escalation_48_sent": False,
                    }
                )
                leave._notify_leave_applied()
                leave._schedule_manager_activity()

        if "request_date_from" in vals or "request_date_to" in vals:
            self._check_request_window()

        return result

    def action_approve(self, check_state=True):
        self._check_no_self_approval()
        backdated_for_manager = self.filtered(
            lambda leave: leave.state == "confirm" and leave._is_backdated_request() and not leave._is_hr_actor()
        )
        regular = self - backdated_for_manager

        if regular:
            super(HrLeave, regular).action_approve(check_state=check_state)

        if backdated_for_manager:
            backdated_for_manager._check_approval_update("validate1")
            current_employee = self.env.user.employee_id
            backdated_for_manager.write(
                {
                    "state": "validate1",
                    "first_approver_id": current_employee.id,
                }
            )
            for leave in backdated_for_manager:
                leave._schedule_hr_activity()
                leave.message_post(
                    body=_(
                        "Backdated leave received manager approval and is now waiting for HR final approval."
                    )
                )
            backdated_for_manager.activity_update()

        return True

    def action_validate(self, check_state=True):
        self._check_no_self_approval()
        if any(leave._is_backdated_request() and leave.state == "confirm" for leave in self):
            raise UserError(
                _("Backdated leave must be manager-approved first before final validation.")
            )

        pending_hr = self.filtered(lambda leave: leave._is_backdated_request() and leave.state == "validate1")
        if pending_hr and not self._is_hr_actor():
            raise AccessError(_("Only HR can perform final approval for backdated leave."))

        result = super().action_validate(check_state=check_state)

        for leave in self:
            leave.message_post(body=_("Time off request approved."))
            leave._notify_leave_approved()

        return result

    def action_refuse(self):
        self._check_no_self_approval()
        result = super().action_refuse()
        for leave in self:
            leave.write(
                {
                    "resonnocare_cancel_request_state": "none",
                    "resonnocare_cancel_decided_by": False,
                    "resonnocare_cancel_decided_on": False,
                }
            )
            leave._notify_leave_declined()
        return result

    def _check_no_self_approval(self):
        for leave in self:
            if leave._is_self_leave_request() and not leave._is_hr_actor():
                raise AccessError(_("You cannot approve or refuse your own leave request."))

    def _action_user_cancel(self, reason):
        self.ensure_one()

        if self._salary_processed_for_leave():
            raise ValidationError(
                _("Cancellation is blocked because salary is already processed for this leave period.")
            )

        today = fields.Date.context_today(self)
        if self.request_date_from and self.request_date_from < today and not (
            self._is_leave_manager_actor() or self._is_hr_actor()
        ):
            self.write(
                {
                    "resonnocare_cancel_request_state": "requested",
                    "resonnocare_cancel_request_reason": reason,
                    "resonnocare_cancel_requested_by": self.env.user.id,
                    "resonnocare_cancel_requested_on": fields.Datetime.now(),
                    "resonnocare_cancel_decided_by": False,
                    "resonnocare_cancel_decided_on": False,
                }
            )
            self._schedule_manager_activity()
            self._notify_cancellation_requested()
            self.message_post(
                body=_("Past-date cancellation requested and sent for manager approval.")
            )
            return True

        return super()._action_user_cancel(reason)

    def action_approve_cancel_request(self):
        for leave in self:
            if leave.resonnocare_cancel_request_state != "requested":
                raise UserError(_("Only pending cancellation requests can be approved."))
            if not (leave._is_leave_manager_actor() or leave._is_hr_actor()):
                raise AccessError(_("Only the manager or HR can approve this cancellation request."))
            if leave._salary_processed_for_leave():
                raise ValidationError(
                    _("Cancellation is blocked because salary is already processed for this leave period.")
                )

            leave._force_cancel(
                leave.resonnocare_cancel_request_reason or _("Cancellation approved by manager/HR."),
                notify_responsibles=False,
            )
            leave.write(
                {
                    "resonnocare_cancel_request_state": "approved",
                    "resonnocare_cancel_decided_by": self.env.user.id,
                    "resonnocare_cancel_decided_on": fields.Datetime.now(),
                }
            )
            leave._notify_cancellation_decision(approved=True)

    def action_reject_cancel_request(self):
        for leave in self:
            if leave.resonnocare_cancel_request_state != "requested":
                raise UserError(_("Only pending cancellation requests can be rejected."))
            if not (leave._is_leave_manager_actor() or leave._is_hr_actor()):
                raise AccessError(_("Only the manager or HR can reject this cancellation request."))

            leave.write(
                {
                    "resonnocare_cancel_request_state": "rejected",
                    "resonnocare_cancel_decided_by": self.env.user.id,
                    "resonnocare_cancel_decided_on": fields.Datetime.now(),
                }
            )
            leave._notify_cancellation_decision(approved=False)
            leave.message_post(body=_("Past-date cancellation request was rejected."))

    @api.model
    def _cron_leave_manager_reminder_24h(self):
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        leaves = self.search(
            [
                ("state", "=", "confirm"),
                ("resonnocare_submitted_on", "!=", False),
                ("resonnocare_submitted_on", "<=", cutoff),
                ("resonnocare_reminder_24_sent", "=", False),
            ]
        )

        for leave in leaves:
            manager_user = leave._get_leave_manager_user()
            if manager_user:
                leave._notify_partners(
                    manager_user.partner_id,
                    _("Reminder: Time off pending approval"),
                    _(
                        "Time off request %(leave)s for %(employee)s is pending your approval for over 24 hours.",
                        leave=leave.display_name,
                        employee=leave.employee_id.name,
                    ),
                )
                leave._schedule_manager_activity()
            leave.resonnocare_reminder_24_sent = True

    @api.model
    def _cron_leave_manager_escalation_48h(self):
        cutoff = fields.Datetime.now() - timedelta(hours=48)
        leaves = self.search(
            [
                ("state", "=", "confirm"),
                ("resonnocare_submitted_on", "!=", False),
                ("resonnocare_submitted_on", "<=", cutoff),
                ("resonnocare_escalation_48_sent", "=", False),
            ]
        )

        for leave in leaves:
            manager_user = leave._get_leave_manager_user()
            functional_manager_partner = leave.employee_id.functional_manager_id.user_id.partner_id

            partners = self.env["res.partner"]
            if manager_user:
                partners |= manager_user.partner_id
            if functional_manager_partner:
                partners |= functional_manager_partner

            if partners:
                leave._notify_partners(
                    partners,
                    _("Escalation: Time off pending approval"),
                    _(
                        "Time off request %(leave)s for %(employee)s is pending for over 48 hours.",
                        leave=leave.display_name,
                        employee=leave.employee_id.name,
                    ),
                )
            leave.resonnocare_escalation_48_sent = True

    @api.model
    def _get_resonnocare_paid_leave_type(self):
        return self.env["hr.leave.type"].search(
            [
                "|",
                ("name", "ilike", "Paid Leave"),
                ("name", "ilike", "PL"),
            ],
            limit=1,
        )

    @api.model
    def _get_resonnocare_lwp_leave_type(self):
        return self.env["hr.leave.type"].search(
            [
                "|",
                "|",
                ("name", "ilike", "Leave Without Pay"),
                ("name", "ilike", "LWP"),
                ("name", "ilike", "Unpaid"),
            ],
            limit=1,
        )

    @api.model
    def _resonnocare_allocation_error(self, error):
        message = (str(error) or "").lower()
        tokens = (
            "no valid allocation",
            "allocation to cover",
            "not enough time off",
            "insufficient",
            "not enough leaves",
        )
        return any(token in message for token in tokens)

    @api.model
    def _resonnocare_with_lwp_vals(self, vals_list):
        pl_type = self._get_resonnocare_paid_leave_type()
        lwp_type = self._get_resonnocare_lwp_leave_type()
        if not (pl_type and lwp_type):
            return vals_list, False

        switched = False
        prepared = []
        for vals in vals_list:
            new_vals = dict(vals)
            if new_vals.get("holiday_status_id") == pl_type.id:
                new_vals["holiday_status_id"] = lwp_type.id
                switched = True
            prepared.append(new_vals)
        return prepared, switched

    @api.model
    def _compute_resonnocare_monthly_pl_credit(self, employee, target_date):
        """21/yr => 1.75/month with DOJ pro-rata in joining month."""
        monthly_credit = 1.75
        doj = employee.joining_date
        if not doj:
            return monthly_credit

        if doj.year != target_date.year or doj.month != target_date.month:
            return monthly_credit

        days_in_month = calendar.monthrange(target_date.year, target_date.month)[1]
        if doj.day > days_in_month:
            return 0.0

        remaining_days = days_in_month - doj.day + 1
        prorata = monthly_credit * (remaining_days / float(days_in_month))
        return round(prorata, 2)

    @api.model
    def _cron_monthly_pl_accrual(self):
        leave_type = self._get_resonnocare_paid_leave_type()
        if not leave_type:
            return True

        today = fields.Date.today()
        month_key = today.strftime("%Y-%m")
        employees = self.env["hr.employee"].sudo().search(
            [
                ("active", "=", True),
                ("joining_date", "!=", False),
                ("joining_date", "<=", today),
            ]
        )
        allocation_model = self.env["hr.leave.allocation"].sudo()

        for employee in employees:
            # Avoid duplicate monthly credits for same employee/leave type.
            allocation_name = f"Auto PL Accrual {month_key}"
            existing = allocation_model.search(
                [
                    ("employee_id", "=", employee.id),
                    ("holiday_status_id", "=", leave_type.id),
                    ("name", "=", allocation_name),
                    ("state", "!=", "refuse"),
                ],
                limit=1,
            )
            if existing:
                continue

            credit = self._compute_resonnocare_monthly_pl_credit(employee, today)
            if credit <= 0:
                continue

            vals = {
                "name": allocation_name,
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "number_of_days": credit,
                "allocation_type": "regular",
                "date_from": today.replace(day=1),
                "date_to": today.replace(day=calendar.monthrange(today.year, today.month)[1]),
                "notes": _(
                    "Auto monthly PL accrual as per policy (1.75/month, DOJ pro-rata in joining month)."
                ),
            }
            allocation = allocation_model.create(vals)
            if hasattr(allocation, "action_validate"):
                allocation.action_validate()
        return True
