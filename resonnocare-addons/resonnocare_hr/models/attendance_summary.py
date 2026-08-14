from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ResonnocareAttendanceSummary(models.Model):
    _name = "resonnocare.attendance.summary"
    _description = "Daily Attendance Evaluation Summary"
    _order = "date desc, employee_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, ondelete="cascade")
    date = fields.Date(string="Date", required=True)
    
    # Evaluation Results
    total_worked_hours = fields.Float(string="Total Worked Hours")
    is_late = fields.Boolean(string="Late Instance")
    is_missing_punch = fields.Boolean(string="Missing Punch")
    
    status = fields.Selection([
        ('present', 'Full Day Present'),
        ('half_day', 'Half Day Present'),
        ('absent', 'Absent'),
        ('holiday', 'Holiday / Week-Off')
    ], string="Calculated Status", default='absent')
    
    # Audit & Links
    attendance_ids = fields.Many2many("hr.attendance", string="Linked Attendances")
    leave_id = fields.Many2one("hr.leave", string="Linked Leave (Deduction/Approved)")
    regularization_ids = fields.One2many(
        "resonnocare.attendance.regularization",
        "attendance_summary_id",
        string="Regularizations",
    )
    regularization_count = fields.Integer(compute="_compute_regularization_count")
    deduction_alert = fields.Selection(
        [("yes", "! Deduction Triggered")],
        string="Deduction Alert",
        compute="_compute_deduction_alert",
    )
    deduction_alert_reason = fields.Char(
        string="Deduction Reason",
        compute="_compute_deduction_alert",
    )
    payroll_locked = fields.Boolean(
        string="Cycle Locked",
        default=False,
        copy=False,
        readonly=True,
    )
    payroll_locked_on = fields.Datetime(
        string="Locked On",
        readonly=True,
        copy=False,
    )
    payroll_window_started_on = fields.Datetime(
        string="Manager Review Window Started On",
        readonly=True,
        copy=False,
    )
    payroll_window_deadline = fields.Datetime(
        string="Manager Review Window Deadline",
        readonly=True,
        copy=False,
    )
    payroll_deduction_days = fields.Float(
        string="Payroll Deduction Days",
        compute="_compute_payroll_impact",
        store=True,
    )
    payroll_deduction_type = fields.Selection(
        [
            ("none", "None"),
            ("pl", "Paid Leave (PL)"),
            ("lwp", "Leave Without Pay (LWP)"),
        ],
        string="Payroll Deduction Type",
        compute="_compute_payroll_impact",
        store=True,
    )
    has_pending_leave = fields.Boolean(
        string="Pending Leave Flag",
        compute="_compute_pending_leave_flag",
        store=True,
    )
    cycle_payable_days = fields.Float(
        string="Cycle Payable Days",
        compute="_compute_cycle_payable_days",
    )
    cycle_lop_days = fields.Float(
        string="Cycle LOP Days",
        compute="_compute_cycle_payable_days",
    )
    cycle_total_days = fields.Float(
        string="Cycle Total Days",
        compute="_compute_cycle_payable_days",
    )
    
    _sql_constraints = [
        ('employee_date_unique', 'unique(employee_id, date)', 'Evaluation already exists for this employee and date.')
    ]

    def _compute_regularization_count(self):
        for record in self:
            record.regularization_count = len(record.regularization_ids)

    def _compute_deduction_alert(self):
        for record in self:
            alert = False
            reason = False

            if record.is_missing_punch:
                alert = True
                reason = _("Missing punch")
            elif record.is_late and record.status == "half_day":
                alert = True
                reason = _("Late coming penalty")
            elif record.status == "half_day":
                alert = True
                reason = _("Half-day policy deduction")
            elif record.status == "absent":
                alert = True
                reason = _("Absent / LWP deduction")
            elif record.leave_id and record.status in ("half_day", "absent"):
                alert = True
                reason = _("Auto leave deduction linked")

            record.deduction_alert = "yes" if alert else False
            record.deduction_alert_reason = reason

    def _is_auto_deduction_leave(self, leave):
        leave_name = (leave.name or "").lower()
        leave_notes = (leave.notes or "").lower()
        return (
            "auto-lwp deduction" in leave_name
            or "auto-pl deduction" in leave_name
            or "automatically created from attendance policy evaluation" in leave_notes
        )

    def _clear_auto_deduction_leave(self):
        self.ensure_one()
        leave = self.leave_id
        if not leave or not self._is_auto_deduction_leave(leave):
            return

        # Reverse system-generated deduction leave when attendance is corrected.
        if leave.state not in ("refuse", "cancel"):
            try:
                leave.sudo().action_refuse()
            except Exception:
                # If refusal is not possible in current workflow state,
                # still unlink from summary so payroll/alerts stop treating it as active deduction.
                pass
        self.leave_id = False

    @api.depends("status", "leave_id", "leave_id.holiday_status_id", "is_missing_punch")
    def _compute_payroll_impact(self):
        for record in self:
            deduction_days = 0.0
            deduction_type = "none"

            if record.status == "half_day":
                deduction_days = 0.5
            elif record.status == "absent":
                deduction_days = 1.0

            if deduction_days > 0:
                leave_type_name = (record.leave_id.holiday_status_id.name or "").lower() if record.leave_id else ""
                if "unpaid" in leave_type_name or "lwp" in leave_type_name:
                    deduction_type = "lwp"
                elif record.leave_id:
                    deduction_type = "pl"
                else:
                    # No linked leave but deduction exists; treat as LWP impact for payroll.
                    deduction_type = "lwp"

            record.payroll_deduction_days = deduction_days
            record.payroll_deduction_type = deduction_type

    @api.depends("employee_id", "date")
    def _compute_pending_leave_flag(self):
        pending_states = {"confirm", "validate1"}
        for record in self:
            pending = False
            if record.employee_id and record.date and "hr.leave" in self.env:
                pending = bool(
                    self.env["hr.leave"].sudo().search_count(
                        [
                            ("employee_id", "=", record.employee_id.id),
                            ("request_date_from", "<=", record.date),
                            ("request_date_to", ">=", record.date),
                            ("state", "in", list(pending_states)),
                        ]
                    )
                )
            record.has_pending_leave = pending

    @api.depends("employee_id", "date", "payroll_deduction_days", "payroll_deduction_type")
    def _compute_cycle_payable_days(self):
        for record in self:
            record.cycle_payable_days = 0.0
            record.cycle_lop_days = 0.0
            record.cycle_total_days = 0.0
            if not record.employee_id or not record.date:
                continue

            if record.date.day >= 26:
                cycle_start = record.date.replace(day=26)
                if record.date.month == 12:
                    cycle_end = record.date.replace(year=record.date.year + 1, month=1, day=25)
                else:
                    cycle_end = record.date.replace(month=record.date.month + 1, day=25)
            else:
                cycle_end = record.date.replace(day=25)
                if record.date.month == 1:
                    cycle_start = record.date.replace(year=record.date.year - 1, month=12, day=26)
                else:
                    cycle_start = record.date.replace(month=record.date.month - 1, day=26)

            summaries = self.search(
                [
                    ("employee_id", "=", record.employee_id.id),
                    ("date", ">=", cycle_start),
                    ("date", "<=", cycle_end),
                ]
            )
            lop_days = sum(
                summaries.filtered(lambda s: s.payroll_deduction_type == "lwp").mapped(
                    "payroll_deduction_days"
                )
            )

            basis_days = ((cycle_end - cycle_start).days + 1)
            contract = (
                self.env["hr.contract"].sudo().search(
                    [
                        ("employee_id", "=", record.employee_id.id),
                        ("state", "=", "open"),
                    ],
                    order="date_start desc, id desc",
                    limit=1,
                )
                if "hr.contract" in self.env
                else False
            )
            if contract and "res_payroll_day_basis" in contract._fields:
                if contract.res_payroll_day_basis == "fixed_26":
                    basis_days = 26.0
                elif contract.res_payroll_day_basis == "fixed_30":
                    basis_days = 30.0

            record.cycle_total_days = basis_days
            record.cycle_lop_days = lop_days
            record.cycle_payable_days = max(basis_days - lop_days, 0.0)

    def action_evaluate_daily(self):
        if any(record.payroll_locked for record in self):
            raise UserError(_("Attendance cycle is locked for one or more selected records."))
        self._evaluate_attendance()

    def action_open_regularizations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendance Regularizations"),
            "res_model": "resonnocare.attendance.regularization",
            "view_mode": "list,form",
            "domain": [("attendance_summary_id", "=", self.id)],
            "context": {
                "default_employee_id": self.employee_id.id,
                "default_date": self.date,
                "default_attendance_summary_id": self.id,
            },
        }

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

        return self.env["resonnocare.attendance.policy"].search(domain, order="priority asc, id asc", limit=1)

    def _to_employee_local(self, dt_utc):
        self.ensure_one()
        if not dt_utc:
            return False
        user_tz = self.employee_id.user_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.UTC.localize(dt_utc)
        return dt_utc.astimezone(tz)

    def _get_shift_start_local(self, target_date):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id
        if not calendar:
            return False

        weekday = str(target_date.weekday())
        day_slots = calendar.attendance_ids.filtered(lambda a: a.dayofweek == weekday)
        if not day_slots:
            return False

        first_slot = min(day_slots, key=lambda s: s.hour_from)
        hours_float = first_slot.hour_from or 0.0
        hour = int(hours_float)
        minute = int(round((hours_float - hour) * 60))

        user_tz = self.employee_id.user_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(user_tz)
        local_dt = datetime.combine(target_date, time(hour=hour, minute=minute))
        return tz.localize(local_dt)

    def _is_working_day(self, target_date):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id
        weekday = target_date.weekday()
        weekly_off_pattern = self.employee_id.resonnocare_weekly_off_pattern

        # Use the explicit employee weekly-off mapping first.
        # `rotational` and `none` should not auto-mark a day as week-off.
        if weekly_off_pattern == "sun" and weekday == 6:
            return False
        if weekly_off_pattern == "sat_sun" and weekday in (5, 6):
            return False

        if calendar:
            weekday_str = str(weekday)
            has_shift = bool(calendar.attendance_ids.filtered(lambda a: a.dayofweek == weekday_str))
            # Missing shift lines should not silently convert the day into Holiday/Week-Off
            # for rotational/no-fixed-off employees.
            if not has_shift and weekly_off_pattern in ("sun", "sat_sun"):
                return False
            if calendar.global_leave_ids.filtered(
                lambda l: l.date_from.date() <= target_date <= l.date_to.date()
            ):
                return False

        holiday_model = self.env["resonnocare.holiday.calendar"]
        if holiday_model.is_holiday_for_employee(self.employee_id, target_date):
            return False
        return True

    def _get_month_late_count(self):
        self.ensure_one()
        month_start = self.date.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        return self.search_count(
            [
                ("employee_id", "=", self.employee_id.id),
                ("date", ">=", month_start),
                ("date", "<=", month_end),
                ("id", "!=", self.id),
                ("is_late", "=", True),
            ]
        )

    def _get_paid_leave_type(self):
        return self.env["hr.leave.type"].search(
            [
                "|",
                ("name", "ilike", "Paid Leave"),
                ("name", "ilike", "PL"),
            ],
            limit=1,
        )

    def _get_unpaid_leave_type(self):
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

    def _get_remaining_leave_days(self, leave_type, employee):
        if not leave_type:
            return 0.0
        leave_type = leave_type.with_context(employee_id=employee.id)
        for field_name in ("virtual_remaining_leaves", "remaining_leaves"):
            if field_name in leave_type._fields:
                return leave_type[field_name] or 0.0
        return 0.0

    def _create_deduction_leave(self, leave_type, days, reason):
        self.ensure_one()
        if not leave_type or days <= 0:
            return False
        existing = self.env["hr.leave"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("request_date_from", "<=", self.date),
                ("request_date_to", ">=", self.date),
                ("state", "!=", "refuse"),
            ],
            limit=1,
        )
        if existing:
            self.leave_id = existing.id
            return existing

        leave = self.env["hr.leave"].create(
            {
                "name": reason,
                "employee_id": self.employee_id.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": self.date,
                "request_date_to": self.date,
                "number_of_days": days,
                "notes": "Automatically created from attendance policy evaluation.",
            }
        )
        self.leave_id = leave.id
        return leave

    def _apply_half_day_deduction(self):
        self.ensure_one()
        pl_type = self._get_paid_leave_type()
        lwp_type = self._get_unpaid_leave_type()
        if pl_type and self._get_remaining_leave_days(pl_type, self.employee_id) >= 0.5:
            return self._create_deduction_leave(pl_type, 0.5, f"Auto-PL deduction: Half day on {self.date}")
        return self._create_deduction_leave(lwp_type, 0.5, f"Auto-LWP deduction: Half day on {self.date}")

    def _apply_full_day_lwp(self, reason):
        self.ensure_one()
        lwp_type = self._get_unpaid_leave_type()
        return self._create_deduction_leave(lwp_type, 1.0, reason)

    def _create_compoff_allocation(self, validity_days):
        self.ensure_one()
        holiday_type = self.env["hr.leave.type"].search([("name", "ilike", "Comp%")], limit=1)
        if not holiday_type:
            return False

        # Comp-Off policy requires manager approval workflow.
        if (
            "allocation_validation_type" in holiday_type._fields
            and holiday_type.allocation_validation_type == "no_validation"
        ):
            holiday_type.sudo().write({"allocation_validation_type": "manager"})

        existing = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("holiday_status_id", "=", holiday_type.id),
                ("date_from", "=", self.date),
                ("number_of_days", "=", 1.0),
                ("state", "!=", "refuse"),
            ],
            limit=1,
        )
        if existing:
            return existing

        return self.env["hr.leave.allocation"].create(
            {
                "name": f"CompOff Credit Request: Worked on {self.date}",
                "employee_id": self.employee_id.id,
                "holiday_status_id": holiday_type.id,
                "number_of_days": 1.0,
                "allocation_type": "regular",
                "date_from": self.date,
                "date_to": self.date + timedelta(days=validity_days),
                "notes": "Auto-generated by attendance on holiday/week-off. Pending manager approval.",
            }
        )

    def _evaluate_attendance(self):
        for record in self:
            if record.payroll_locked:
                continue
            policy = record._resolve_policy()
            start_dt = datetime.combine(record.date, datetime.min.time())
            end_dt = datetime.combine(record.date, datetime.max.time())

            attendances = self.env["hr.attendance"].search(
                [
                    ("employee_id", "=", record.employee_id.id),
                    ("check_in", ">=", start_dt),
                    ("check_in", "<=", end_dt),
                ]
            )
            record.attendance_ids = [(6, 0, attendances.ids)]

            total_hours = sum(att.worked_hours for att in attendances)
            break_hours = 0.0
            if policy and policy.auto_deduct_break and total_hours > 0 and policy.mandatory_break_minutes > 0:
                break_hours = min(total_hours, policy.mandatory_break_minutes / 60.0)
            net_hours = max(total_hours - break_hours, 0.0)
            record.total_worked_hours = net_hours

            is_missing = any(not att.check_out for att in attendances)
            record.is_missing_punch = is_missing

            full_day_min = policy.full_day_min_hours if policy else 8.0
            half_day_min = policy.half_day_min_hours if policy else 4.0
            is_working_day = record._is_working_day(record.date)

            if net_hours >= full_day_min:
                record.status = "present"
            elif net_hours >= half_day_min:
                record.status = "half_day"
            else:
                record.status = "absent" if is_working_day else "holiday"

            if not is_working_day and net_hours >= full_day_min:
                validity_days = policy.compoff_validity_days if policy else 30
                record._create_compoff_allocation(validity_days)

            if (
                is_working_day
                and is_missing
                and (not policy or policy.auto_mark_absent_on_missing_punch)
            ):
                record.status = "absent"
                if not policy or policy.auto_create_lwp_for_absent:
                    record._apply_full_day_lwp(
                        f"Auto-LWP deduction: Missing punch on {record.date}"
                    )

            record.is_late = False
            if attendances and is_working_day:
                first_check_in = min(attendances.mapped("check_in"))
                first_check_in_local = record._to_employee_local(first_check_in)
                shift_start_local = record._get_shift_start_local(record.date)
                if first_check_in_local and shift_start_local:
                    tolerance = policy.late_tolerance_minutes if policy else 15
                    late_cutoff = shift_start_local + timedelta(minutes=tolerance)

                    apply_late = True
                    if policy and not policy.apply_late_penalty:
                        apply_late = False
                    if record.employee_id.attendance_profile == "roaming":
                        apply_late = False

                    if apply_late and first_check_in_local > late_cutoff:
                        record.is_late = True
                        free_late = policy.free_late_per_month if policy else 0
                        month_late_count = record._get_month_late_count()
                        should_penalize = month_late_count >= free_late
                        if should_penalize and (not policy or policy.half_day_penalty_for_late):
                            record.status = "half_day"
                            if not policy or policy.auto_create_half_day_deduction:
                                record._apply_half_day_deduction()

            if record.status == "absent" and is_working_day and (not policy or policy.auto_create_lwp_for_absent):
                record._apply_full_day_lwp(f"Auto-LWP deduction: Absent on {record.date}")

            if record.status == "half_day" and (not policy or policy.auto_create_half_day_deduction):
                record._apply_half_day_deduction()

            if record.status in ("present", "holiday"):
                record._clear_auto_deduction_leave()
                if record.status == "holiday":
                    record.leave_id = False

    @api.model
    def _cron_generate_daily_summary(self):
        yesterday = fields.Date.today() - timedelta(days=1)
        employees = self.env["hr.employee"].search([("active", "=", True)])

        for employee in employees:
            summary = self.search([("employee_id", "=", employee.id), ("date", "=", yesterday)], limit=1)
            if not summary:
                summary = self.create({"employee_id": employee.id, "date": yesterday})
            summary._evaluate_attendance()

    @api.model
    def _cron_weekly_regularization_reminder(self):
        """Weekly nudge to employees for missing-punch days pending regularization."""
        lookback_start = fields.Date.today() - timedelta(days=30)
        summaries = self.search(
            [
                ("date", ">=", lookback_start),
                ("is_missing_punch", "=", True),
                ("employee_id.user_id", "!=", False),
            ],
            order="employee_id, date",
        )
        if not summaries:
            return True

        pending_states = {"draft", "submitted", "manager_approved", "hr_approved"}
        pending_by_employee = {}
        for summary in summaries:
            has_regularization = any(
                regularization.state in pending_states
                for regularization in summary.regularization_ids
            )
            if has_regularization:
                continue
            pending_by_employee.setdefault(summary.employee_id, []).append(summary.date)

        for employee, pending_dates in pending_by_employee.items():
            user = employee.user_id
            if not user or not user.partner_id:
                continue
            pretty_dates = ", ".join(fields.Date.to_string(day) for day in pending_dates)
            employee.message_post(
                subject=_("Weekly Reminder: Attendance Regularization Pending"),
                body=_(
                    "Please regularize your missing punch records for: %(dates)s.",
                    dates=pretty_dates,
                ),
                partner_ids=[user.partner_id.id],
                message_type="notification",
                subtype_xmlid="mail.mt_comment",
            )
        return True

    @api.model
    def _get_nth_working_day_of_month(self, anchor_date, n):
        """Return the N-th weekday (Mon-Fri) of anchor_date's month."""
        target = max(int(n or 1), 1)
        cursor = anchor_date.replace(day=1)
        month = cursor.month
        count = 0
        last_working_day = cursor

        while cursor.month == month:
            if cursor.weekday() < 5:
                count += 1
                last_working_day = cursor
                if count >= target:
                    return cursor
            cursor += timedelta(days=1)

        return last_working_day

    @api.model
    def _cron_close_attendance_cycle(self):
        """
        Start manager review window once cutoff 25th 23:59 is crossed.
        Cycle window: 26th previous month -> 25th current month.
        """
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        policy = self.env["resonnocare.attendance.policy"].search([("active", "=", True)], order="priority asc, id asc", limit=1)
        close_day = policy.attendance_cycle_close_day if policy and policy.attendance_cycle_close_day else 25
        cycle_start_day = 26

        # Enforce strict lock trigger only after 25th 23:59 local/server time.
        if today.day < close_day:
            return True
        if today.day == close_day:
            cutoff_dt = now.replace(
                year=today.year,
                month=today.month,
                day=close_day,
                hour=23,
                minute=59,
                second=0,
                microsecond=0,
            )
            if now < cutoff_dt:
                return True
        # Run only from cycle start day onward to match 26th cycle rollover.
        if today.day < cycle_start_day and today.day != close_day:
            return True

        # Cycle ending date is close_day (25) of current month.
        cycle_end = today.replace(day=close_day)
        prev_month_last_day = today.replace(day=1) - timedelta(days=1)
        cycle_start = prev_month_last_day.replace(day=cycle_start_day)

        to_lock = self.search(
            [
                ("date", ">=", cycle_start),
                ("date", "<=", cycle_end),
                ("payroll_locked", "=", False),
                ("payroll_window_started_on", "=", False),
            ]
        )
        if to_lock:
            to_lock.write(
                {
                    "payroll_window_started_on": now,
                    "payroll_window_deadline": now + timedelta(hours=24),
                }
            )
        return True

    @api.model
    def _cron_finalize_attendance_cycle(self):
        """
        Finalize payroll lock after manager review window (24h) ends.
        """
        now = fields.Datetime.now()
        to_lock = self.search(
            [
                ("payroll_locked", "=", False),
                ("payroll_window_started_on", "!=", False),
                ("payroll_window_deadline", "!=", False),
                ("payroll_window_deadline", "<=", now),
            ]
        )
        if to_lock:
            to_lock.write(
                {
                    "payroll_locked": True,
                    "payroll_locked_on": now,
                }
            )
        return True

    @api.model
    def _cron_salary_day_freeze(self):
        """
        On configured salary day (interpreted as N-th working day), ensure
        previous-month attendance is frozen.
        """
        today = fields.Date.today()
        policy = self.env["resonnocare.attendance.policy"].search(
            [("active", "=", True)],
            order="priority asc, id asc",
            limit=1,
        )
        salary_day = policy.salary_day if policy and policy.salary_day else 1
        salary_freeze_date = self._get_nth_working_day_of_month(today, salary_day)
        if today < salary_freeze_date:
            return True

        current_month_start = today.replace(day=1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        to_lock = self.search(
            [
                ("date", ">=", prev_month_start),
                ("date", "<=", prev_month_end),
                ("payroll_locked", "=", False),
            ]
        )
        if to_lock:
            to_lock.write(
                {
                    "payroll_locked": True,
                    "payroll_locked_on": fields.Datetime.now(),
                }
            )
        return True
