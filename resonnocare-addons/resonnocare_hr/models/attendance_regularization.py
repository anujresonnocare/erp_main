from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ResonnocareAttendanceRegularization(models.Model):
    _name = "resonnocare.attendance.regularization"
    _description = "Attendance Regularization Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        default=lambda self: self.env.user.employee_id.id,
        tracking=True,
    )
    date = fields.Date(required=True, tracking=True, default=fields.Date.context_today)
    attendance_summary_id = fields.Many2one(
        "resonnocare.attendance.summary",
        string="Attendance Summary",
        readonly=True,
    )

    requested_check_in = fields.Datetime(string="Requested Check In", tracking=True)
    requested_check_out = fields.Datetime(string="Requested Check Out", tracking=True)
    reason = fields.Selection(
        [
            ("forgot_in", "Forgot to Punch In"),
            ("forgot_out", "Forgot to Punch Out"),
            ("missed_punch", "Missed Punch (In/Out)"),
            ("system_error", "System Error"),
            ("on_duty", "On Duty (OD)"),
            ("field_visit", "Field Visit / Field Work"),
            ("official_travel", "Official Travel"),
            ("training", "Training / Workshop"),
            ("wfh", "Work From Home (WFH)"),
            ("late_arrival_adjustment", "Late Arrival Adjustment"),
            ("early_exit_adjustment", "Early Exit Adjustment"),
            ("holiday_working", "Holiday Working"),
            ("weekend_working", "Weekend Working"),
        ],
        required=True,
        tracking=True,
    )
    reason_details = fields.Text(string="Reason Details", tracking=True)
    requires_reason_details = fields.Boolean(compute="_compute_requires_reason_details")

    attachment = fields.Binary(string="Attachment")
    attachment_filename = fields.Char(string="Attachment Filename")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("manager_approved", "Manager Approved"),
            ("hr_approved", "HR Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    submitted_by = fields.Many2one("res.users", readonly=True)
    submitted_on = fields.Datetime(readonly=True)

    manager_id = fields.Many2one("res.users", readonly=True)
    manager_decision_on = fields.Datetime(readonly=True)
    manager_notes = fields.Text()

    hr_id = fields.Many2one("res.users", readonly=True)
    hr_decision_on = fields.Datetime(readonly=True)
    hr_notes = fields.Text()

    reminder_sent = fields.Boolean(default=False, readonly=True)
    escalation_sent = fields.Boolean(default=False, readonly=True)

    @api.depends("employee_id", "date")
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name or _("Employee")
            day = fields.Date.to_string(record.date) if record.date else _("No Date")
            record.name = f"{employee_name} - {day}"

    @api.depends("reason")
    def _compute_requires_reason_details(self):
        for record in self:
            record.requires_reason_details = record.reason in (
                "late_arrival_adjustment",
                "early_exit_adjustment",
            )

    @api.constrains("requested_check_in", "requested_check_out", "date")
    def _check_requested_window(self):
        for record in self:
            if record.requested_check_in and record.requested_check_out:
                if record.requested_check_out <= record.requested_check_in:
                    raise ValidationError(_("Requested check-out must be later than requested check-in."))
            if record.date:
                for dt in (record.requested_check_in, record.requested_check_out):
                    if dt and fields.Datetime.to_datetime(dt).date() != record.date:
                        raise ValidationError(_("Requested check times must belong to the selected date."))

    def _get_manager_user(self):
        self.ensure_one()
        employee = self.employee_id
        attendance_manager = employee._fields.get("attendance_manager_id") and employee.attendance_manager_id
        return (
            employee.leave_manager_id.user_id
            or employee.parent_id.user_id
            or (attendance_manager and attendance_manager.user_id)
        )

    def _is_manager_actor(self):
        self.ensure_one()
        manager_user = self._get_manager_user()
        return bool(manager_user and manager_user.id == self.env.user.id)

    def _is_hr_actor(self):
        return self.env.user.has_group("resonnocare_base.group_resonnocare_hr") or self.env.user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        )

    def _validate_reason_requirements(self):
        self.ensure_one()
        if self.requires_reason_details and not self.reason_details:
            raise ValidationError(_("Reason details are required for this adjustment reason."))

        required_pairs = {
            "forgot_in": ("requested_check_in",),
            "forgot_out": ("requested_check_out",),
            "missed_punch": ("requested_check_in", "requested_check_out"),
            "system_error": ("requested_check_in", "requested_check_out"),
            "on_duty": ("requested_check_in", "requested_check_out"),
            "field_visit": ("requested_check_in", "requested_check_out"),
            "official_travel": ("requested_check_in", "requested_check_out"),
            "training": ("requested_check_in", "requested_check_out"),
            "wfh": ("requested_check_in", "requested_check_out"),
            "holiday_working": ("requested_check_in", "requested_check_out"),
            "weekend_working": ("requested_check_in", "requested_check_out"),
        }
        required_fields = required_pairs.get(self.reason, ())
        for field_name in required_fields:
            if not self[field_name]:
                label = self._fields[field_name].string
                raise ValidationError(_("%s is required for this regularization reason.") % label)

    def _resolve_policy(self):
        self.ensure_one()
        employee = self.employee_id
        domain = [("active", "=", True)]
        if employee.clinic_id:
            domain += ["|", ("clinic_id", "=", employee.clinic_id.id), ("clinic_id", "=", False)]
        else:
            domain += [("clinic_id", "=", False)]

        if employee.attendance_profile:
            domain += [
                "|",
                ("attendance_profile", "=", employee.attendance_profile),
                ("attendance_profile", "=", False),
            ]
        if employee.clinic_role:
            domain += ["|", ("clinic_role", "=", employee.clinic_role), ("clinic_role", "=", False)]

        return self.env["resonnocare.attendance.policy"].search(
            domain, order="priority asc, id asc", limit=1
        )

    def _to_employee_local(self, dt_utc):
        self.ensure_one()
        if not dt_utc:
            return False
        user_tz = self.employee_id.user_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.UTC.localize(dt_utc)
        return dt_utc.astimezone(tz)

    def _get_shift_window_local(self):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id
        if not calendar or not self.date:
            return False, False

        weekday = str(self.date.weekday())
        day_slots = calendar.attendance_ids.filtered(lambda a: a.dayofweek == weekday)
        if not day_slots:
            return False, False

        earliest = min(day_slots.mapped("hour_from"))
        latest = max(day_slots.mapped("hour_to"))

        user_tz = self.employee_id.user_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz)

        start_hour = int(earliest)
        start_minute = int(round((earliest - start_hour) * 60))
        start_local = tz.localize(
            datetime.combine(self.date, time(hour=start_hour, minute=start_minute))
        )

        end_day_offset = int(latest // 24)
        end_hour_float = latest % 24
        end_hour = int(end_hour_float)
        end_minute = int(round((end_hour_float - end_hour) * 60))
        end_date = self.date + timedelta(days=end_day_offset)
        end_local = tz.localize(
            datetime.combine(end_date, time(hour=end_hour, minute=end_minute))
        )
        return start_local, end_local

    def _validate_regularization_shift_alignment(self):
        self.ensure_one()
        employee = self.employee_id
        if not employee or employee.attendance_profile == "roaming":
            return
        if not self.requested_check_in or not self.requested_check_out:
            raise ValidationError(
                _("Both requested check-in and check-out are required for shift-aligned regularization.")
            )

        shift_start_local, shift_end_local = self._get_shift_window_local()
        policy = self._resolve_policy()
        tolerance = policy.late_tolerance_minutes if policy else 15
        min_hours = policy.half_day_min_hours if policy else 4.0

        requested_in_local = self._to_employee_local(self.requested_check_in)
        requested_out_local = self._to_employee_local(self.requested_check_out)
        worked_hours = (requested_out_local - requested_in_local).total_seconds() / 3600.0

        if not shift_start_local or not shift_end_local:
            if self.reason in ("holiday_working", "weekend_working"):
                full_day_min = policy.full_day_min_hours if policy else 8.0
                if worked_hours < full_day_min:
                    raise ValidationError(
                        _(
                            "Holiday/Weekend regularization needs at least %(hours).2f worked hours as per policy.",
                            hours=full_day_min,
                        )
                    )
                return
            raise ValidationError(
                _("No shift is configured for the employee on the selected date. Please configure shift first.")
            )

        latest_allowed_in = shift_start_local + timedelta(minutes=tolerance)
        earliest_allowed_out = shift_end_local - timedelta(minutes=tolerance)

        if requested_in_local > latest_allowed_in:
            raise ValidationError(
                _(
                    "Requested check-in (%(in_time)s) exceeds allowed shift window (latest allowed: %(allowed)s).",
                    in_time=requested_in_local.strftime("%Y-%m-%d %H:%M"),
                    allowed=latest_allowed_in.strftime("%Y-%m-%d %H:%M"),
                )
            )
        if requested_out_local < earliest_allowed_out:
            raise ValidationError(
                _(
                    "Requested check-out (%(out_time)s) is earlier than allowed shift window (earliest allowed: %(allowed)s).",
                    out_time=requested_out_local.strftime("%Y-%m-%d %H:%M"),
                    allowed=earliest_allowed_out.strftime("%Y-%m-%d %H:%M"),
                )
            )

        if worked_hours < min_hours:
            raise ValidationError(
                _(
                    "Regularized punches result in %(hours).2f worked hours, below minimum required %(min_hours).2f hours.",
                    hours=worked_hours,
                    min_hours=min_hours,
                )
            )

    def _get_or_create_summary(self, create_if_missing=True):
        self.ensure_one()
        summary_model = self.env["resonnocare.attendance.summary"].sudo()
        summary = summary_model.search(
            [("employee_id", "=", self.employee_id.id), ("date", "=", self.date)],
            limit=1,
        )
        if not summary and create_if_missing:
            summary = summary_model.create(
                {
                    "employee_id": self.employee_id.id,
                    "date": self.date,
                }
            )
        if summary:
            self.attendance_summary_id = summary.id
        return summary

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            if record.employee_id.user_id and record.employee_id.user_id.id != self.env.user.id and not record._is_hr_actor():
                raise AccessError(_("You can submit regularization only for your own employee profile."))

            record._validate_reason_requirements()
            # Do not create attendance summary in employee submit path to avoid ACL friction.
            # HR flow will create it safely when needed.
            record._get_or_create_summary(create_if_missing=False)

            vals = {
                "state": "submitted",
                "submitted_by": self.env.user.id,
                "submitted_on": fields.Datetime.now(),
            }
            manager_user = record._get_manager_user()
            if manager_user:
                vals["manager_id"] = manager_user.id
            record.write(vals)

            record._schedule_manager_activity()
            record._notify_submitted()

    def action_manager_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be manager-approved."))
            if not (record._is_manager_actor() or record._is_hr_actor()):
                raise AccessError(_("Only assigned manager or HR can perform this action."))

            record.write(
                {
                    "state": "manager_approved",
                    "manager_id": self.env.user.id,
                    "manager_decision_on": fields.Datetime.now(),
                }
            )
            record._schedule_hr_activity()
            record._notify_manager_approved()

    def action_hr_approve(self):
        for record in self:
            if record.state not in ("manager_approved", "submitted"):
                raise UserError(_("Only manager-approved or submitted requests can be HR-approved."))
            if not record._is_hr_actor():
                raise AccessError(_("Only HR can perform final approval."))

            record._validate_regularization_shift_alignment()
            record._apply_regularization()
            record.write(
                {
                    "state": "hr_approved",
                    "hr_id": self.env.user.id,
                    "hr_decision_on": fields.Datetime.now(),
                }
            )

            summary = record._get_or_create_summary()
            summary.action_evaluate_daily()
            record._notify_hr_approved()

    def action_reject(self):
        for record in self:
            if record.state not in ("submitted", "manager_approved"):
                raise UserError(_("Only submitted or manager-approved requests can be rejected."))
            if record.state == "submitted" and not (record._is_manager_actor() or record._is_hr_actor()):
                raise AccessError(_("Only assigned manager or HR can reject at this stage."))
            if record.state == "manager_approved" and not record._is_hr_actor():
                raise AccessError(_("Only HR can reject after manager approval."))

            vals = {"state": "rejected"}
            now = fields.Datetime.now()
            if record.state == "submitted":
                vals.update({"manager_id": self.env.user.id, "manager_decision_on": now})
            else:
                vals.update({"hr_id": self.env.user.id, "hr_decision_on": now})
            record.write(vals)
            record._notify_rejected()

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("Only draft or submitted requests can be cancelled."))
            if record.employee_id.user_id and record.employee_id.user_id.id != self.env.user.id and not record._is_hr_actor():
                raise AccessError(_("You can cancel only your own regularization request."))
            record.state = "cancelled"
            record._notify_cancelled()

    def action_reset_to_draft(self):
        for record in self:
            if not record._is_hr_actor():
                raise AccessError(_("Only HR can reset regularization to draft."))
            record.state = "draft"

    def _domain_for_day_attendance(self):
        self.ensure_one()
        start_dt = datetime.combine(self.date, datetime.min.time())
        end_dt = datetime.combine(self.date, datetime.max.time())
        return [
            ("employee_id", "=", self.employee_id.id),
            ("check_in", ">=", start_dt),
            ("check_in", "<=", end_dt),
        ]

    def _apply_regularization(self):
        self.ensure_one()
        attendances = self.env["hr.attendance"].search(self._domain_for_day_attendance(), order="check_in asc, id asc")
        if not attendances:
            if self.requested_check_in and self.requested_check_out:
                self.env["hr.attendance"].create(
                    {
                        "employee_id": self.employee_id.id,
                        "check_in": self.requested_check_in,
                        "check_out": self.requested_check_out,
                        "resonnocare_punch_source": "regularized",
                        "resonnocare_check_in_regularized": True,
                        "resonnocare_check_out_regularized": True,
                        "resonnocare_regularization_id": self.id,
                        "resonnocare_regularized_by": self.env.user.id,
                        "resonnocare_regularized_on": fields.Datetime.now(),
                    }
                )
            return

        first_attendance = attendances[0]
        last_attendance = attendances[-1]

        if self.requested_check_in:
            if not first_attendance.check_in or self.requested_check_in < first_attendance.check_in:
                first_attendance.write(
                    {
                        "check_in": self.requested_check_in,
                        "resonnocare_punch_source": "regularized",
                        "resonnocare_check_in_regularized": True,
                        "resonnocare_regularization_id": self.id,
                        "resonnocare_regularized_by": self.env.user.id,
                        "resonnocare_regularized_on": fields.Datetime.now(),
                    }
                )
        if self.requested_check_out:
            if not last_attendance.check_out or self.requested_check_out > last_attendance.check_out:
                last_attendance.write(
                    {
                        "check_out": self.requested_check_out,
                        "resonnocare_punch_source": "regularized",
                        "resonnocare_check_out_regularized": True,
                        "resonnocare_regularization_id": self.id,
                        "resonnocare_regularized_by": self.env.user.id,
                        "resonnocare_regularized_on": fields.Datetime.now(),
                    }
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

    def _notify_submitted(self):
        self.ensure_one()
        manager = self._get_manager_user()
        partners = self.env["res.partner"]
        if manager and manager.partner_id:
            partners |= manager.partner_id
        if self.employee_id.functional_manager_id.user_id.partner_id:
            partners |= self.employee_id.functional_manager_id.user_id.partner_id
        self._notify_partners(
            partners,
            _("Attendance Regularization Submitted"),
            _(
                "Regularization request %(request)s for %(employee)s dated %(date)s is pending approval.",
                request=self.display_name,
                employee=self.employee_id.name,
                date=fields.Date.to_string(self.date),
            ),
        )

    def _notify_manager_approved(self):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        self._notify_partners(
            employee_partner,
            _("Attendance Regularization: Manager Approved"),
            _(
                "Your regularization request %(request)s has been approved by manager and sent to HR.",
                request=self.display_name,
            ),
        )

    def _notify_hr_approved(self):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        self._notify_partners(
            employee_partner,
            _("Attendance Regularization Approved"),
            _(
                "Your regularization request %(request)s has been approved by HR and attendance was re-evaluated.",
                request=self.display_name,
            ),
        )

    def _notify_rejected(self):
        self.ensure_one()
        employee_partner = self.employee_id.user_id.partner_id
        if not employee_partner:
            return
        self._notify_partners(
            employee_partner,
            _("Attendance Regularization Rejected"),
            _(
                "Your regularization request %(request)s has been rejected.",
                request=self.display_name,
            ),
        )

    def _notify_cancelled(self):
        self.ensure_one()
        manager = self._get_manager_user()
        partners = self.env["res.partner"]
        if self.employee_id.user_id.partner_id:
            partners |= self.employee_id.user_id.partner_id
        if manager and manager.partner_id:
            partners |= manager.partner_id
        self._notify_partners(
            partners,
            _("Attendance Regularization Cancelled"),
            _(
                "Regularization request %(request)s for %(employee)s has been cancelled.",
                request=self.display_name,
                employee=self.employee_id.name,
            ),
        )

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
            note=_("Attendance regularization request requires your action."),
            date_deadline=fields.Date.today(),
        )

    def _schedule_manager_activity(self):
        self.ensure_one()
        manager_user = self._get_manager_user()
        if manager_user:
            self._schedule_activity_if_missing(
                manager_user,
                _("Regularization pending manager approval"),
            )

    def _schedule_hr_activity(self):
        self.ensure_one()
        hr_user = self.env["res.users"].search(
            [("groups_id", "in", self.env.ref("resonnocare_base.group_resonnocare_hr").id)],
            limit=1,
        )
        if hr_user:
            self._schedule_activity_if_missing(
                hr_user,
                _("Regularization pending HR approval"),
            )

    @api.model
    def _cron_regularization_reminder(self):
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        records = self.search(
            [
                ("state", "=", "submitted"),
                ("submitted_on", "<=", cutoff),
                ("reminder_sent", "=", False),
            ]
        )
        for record in records:
            record._schedule_manager_activity()
            manager = record._get_manager_user()
            if manager and manager.partner_id:
                record._notify_partners(
                    manager.partner_id,
                    _("Reminder: Attendance Regularization Pending"),
                    _(
                        "Regularization request %(request)s for %(employee)s has been pending for over 24 hours.",
                        request=record.display_name,
                        employee=record.employee_id.name,
                    ),
                )
            record.reminder_sent = True

    @api.model
    def _cron_regularization_escalation(self):
        cutoff = fields.Datetime.now() - timedelta(hours=48)
        records = self.search(
            [
                ("state", "=", "submitted"),
                ("submitted_on", "<=", cutoff),
                ("escalation_sent", "=", False),
            ]
        )
        for record in records:
            record._schedule_hr_activity()
            partners = self.env["res.partner"]
            hr_group = self.env.ref("resonnocare_base.group_resonnocare_hr", raise_if_not_found=False)
            if hr_group:
                partners |= hr_group.users.mapped("partner_id")
            manager = record._get_manager_user()
            if manager and manager.partner_id:
                partners |= manager.partner_id
            record._notify_partners(
                partners,
                _("Escalation: Attendance Regularization Pending"),
                _(
                    "Regularization request %(request)s for %(employee)s has been pending for over 48 hours.",
                    request=record.display_name,
                    employee=record.employee_id.name,
                ),
            )
            record.escalation_sent = True
