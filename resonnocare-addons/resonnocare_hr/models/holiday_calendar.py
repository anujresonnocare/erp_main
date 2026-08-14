import logging
from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ResonnocareHolidayCalendar(models.Model):
    _name = "resonnocare.holiday.calendar"
    _description = "Resonnocare Holiday Calendar"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    scope = fields.Selection(
        [
            ("global", "Global"),
            ("region", "Region"),
            ("state", "State"),
            ("clinic", "Clinic"),
        ],
        required=True,
        default="global",
    )
    region_id = fields.Many2one("res.country.group", string="Region")
    state_id = fields.Many2one("res.country.state", string="State")
    clinic_id = fields.Many2one("resonnocare.clinic", string="Clinic")
    description = fields.Text()
    scope_display = fields.Char(
        string="Scope",
        compute="_compute_scope_labels",
    )
    scope_target_display = fields.Char(
        string="Applies To",
        compute="_compute_scope_labels",
    )

    def _register_hook(self):
        result = super()._register_hook()
        try:
            self.sudo().search([])._sync_resource_calendar_holidays()
        except Exception as exc:
            self.env.cr.rollback()
            _logger.warning("Skipped holiday-to-timeoff sync in _register_hook: %s", exc)
        return result

    @api.depends("scope", "clinic_id", "state_id", "region_id")
    def _compute_scope_labels(self):
        scope_labels = dict(self._fields["scope"].selection)
        for record in self:
            record.scope_display = scope_labels.get(record.scope, record.scope or "")
            if record.scope == "clinic":
                record.scope_target_display = record.clinic_id.name or ""
            elif record.scope == "state":
                record.scope_target_display = record.state_id.name or ""
            elif record.scope == "region":
                record.scope_target_display = record.region_id.name or ""
            else:
                record.scope_target_display = _("All Locations")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_to < record.date_from:
                raise ValidationError(_("Holiday end date cannot be before start date."))

    @api.constrains("scope", "region_id", "state_id", "clinic_id")
    def _check_scope_fields(self):
        for record in self:
            if record.scope == "region" and not record.region_id:
                raise ValidationError(_("Region is required when scope is Region."))
            if record.scope == "state" and not record.state_id:
                raise ValidationError(_("State is required when scope is State."))
            if record.scope == "clinic" and not record.clinic_id:
                raise ValidationError(_("Clinic is required when scope is Clinic."))

    def _scope_domain(self):
        self.ensure_one()
        domain = [("scope", "=", self.scope)]
        if self.scope == "region":
            domain.append(("region_id", "=", self.region_id.id))
        elif self.scope == "state":
            domain.append(("state_id", "=", self.state_id.id))
        elif self.scope == "clinic":
            domain.append(("clinic_id", "=", self.clinic_id.id))
        return domain

    @api.model
    def _holiday_days_in_year(self, record, year):
        start = record.date_from
        end = record.date_to or record.date_from
        if not start or not end:
            return set()
        year_start = fields.Date.from_string(f"{year}-01-01")
        year_end = fields.Date.from_string(f"{year}-12-31")
        effective_start = max(start, year_start)
        effective_end = min(end, year_end)
        if effective_end < effective_start:
            return set()
        days = set()
        cursor = effective_start
        while cursor <= effective_end:
            days.add(cursor)
            cursor += timedelta(days=1)
        return days

    @api.constrains("active", "date_from", "date_to", "scope", "region_id", "state_id", "clinic_id")
    def _check_annual_holiday_cap(self):
        for record in self:
            if not record.active or not record.date_from:
                continue

            start_year = record.date_from.year
            end_year = (record.date_to or record.date_from).year
            domain = [("active", "=", True)] + record._scope_domain()
            candidates = self.search(domain)

            for year in range(start_year, end_year + 1):
                configured_days = set()
                for holiday in candidates:
                    configured_days |= self._holiday_days_in_year(holiday, year)
                if len(configured_days) > 11:
                    raise ValidationError(
                        _(
                            "Holiday configuration exceeds 11 days for %(scope)s in %(year)s. "
                            "Current configured days: %(count)s.",
                            scope=dict(self._fields["scope"].selection).get(record.scope, record.scope),
                            year=year,
                            count=len(configured_days),
                        )
                    )

    @api.model
    def _scope_rank(self, scope):
        return {"clinic": 4, "state": 3, "region": 2, "global": 1}.get(scope, 0)

    @api.model
    def _is_applicable_for_employee(self, holiday, employee):
        if holiday.scope == "global":
            return True
        if holiday.scope == "clinic":
            return bool(employee.clinic_id and holiday.clinic_id == employee.clinic_id)
        if holiday.scope == "state":
            return bool(employee.resonnocare_state_id and holiday.state_id == employee.resonnocare_state_id)
        if holiday.scope == "region":
            if employee.resonnocare_region_id:
                return bool(holiday.region_id == employee.resonnocare_region_id)
            country = employee.resonnocare_country_id
            return bool(country and holiday.region_id and country in holiday.region_id.country_ids)
        return False

    @api.model
    def is_holiday_for_employee(self, employee, target_date):
        if not employee or not target_date:
            return False

        records = self.search(
            [
                ("active", "=", True),
                ("date_from", "<=", target_date),
                "|",
                ("date_to", "=", False),
                ("date_to", ">=", target_date),
            ]
        )
        if not records:
            return False

        # Client-required hierarchy: Clinic -> State -> Region -> Global.
        clinic_records = records.filtered(
            lambda h: h.scope == "clinic" and self._is_applicable_for_employee(h, employee)
        )
        if clinic_records:
            return True

        state_records = records.filtered(
            lambda h: h.scope == "state" and self._is_applicable_for_employee(h, employee)
        )
        if state_records:
            return True

        region_records = records.filtered(
            lambda h: h.scope == "region" and self._is_applicable_for_employee(h, employee)
        )
        if region_records:
            return True

        global_records = records.filtered(lambda h: h.scope == "global")
        return bool(global_records)

    @api.model
    def get_applicable_holidays_for_employee(self, employee):
        if not employee:
            return self.browse()

        records = self.search([("active", "=", True)])
        clinic_records = records.filtered(
            lambda h: h.scope == "clinic" and self._is_applicable_for_employee(h, employee)
        )
        state_records = records.filtered(
            lambda h: h.scope == "state" and self._is_applicable_for_employee(h, employee)
        )
        region_records = records.filtered(
            lambda h: h.scope == "region" and self._is_applicable_for_employee(h, employee)
        )
        global_records = records.filtered(lambda h: h.scope == "global")
        return clinic_records | state_records | region_records | global_records

    @api.model
    def _get_or_create_public_holiday_leave_type(self):
        leave_type_model = self.env["hr.leave.type"].sudo()
        leave_type = leave_type_model.search(
            [("name", "=", "Public Holiday")],
            limit=1,
        )
        if leave_type:
            update_vals = {}
            if "show_on_dashboard" in leave_type_model._fields and not leave_type.show_on_dashboard:
                update_vals["show_on_dashboard"] = True
            if update_vals:
                leave_type.write(update_vals)
            return leave_type

        vals = {"name": "Public Holiday"}
        if "requires_allocation" in leave_type_model._fields:
            vals["requires_allocation"] = "no"
        if "leave_validation_type" in leave_type_model._fields:
            vals["leave_validation_type"] = "no_validation"
        if "request_unit" in leave_type_model._fields:
            vals["request_unit"] = "day"
        if "show_on_dashboard" in leave_type_model._fields:
            vals["show_on_dashboard"] = True
        return leave_type_model.create(vals)

    def _get_target_employees(self):
        self.ensure_one()
        employees = self.env["hr.employee"].sudo().search([("active", "=", True)])
        return employees.filtered(lambda emp: self._is_applicable_for_employee(self, emp))

    def _sync_calendar_leaves(self):
        leave_model = self.env["hr.leave"].sudo().with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
            resonnocare_holiday_sync=True,
        )
        leave_type = self._get_or_create_public_holiday_leave_type()

        for holiday in self:
            existing = leave_model.search(
                [
                    ("resonnocare_holiday_calendar_id", "=", holiday.id),
                    ("resonnocare_is_calendar_holiday", "=", True),
                ]
            )
            if not holiday.active:
                if existing:
                    existing.unlink()
                continue

            target_employees = holiday._get_target_employees()
            target_employee_ids = set(target_employees.ids)
            existing_by_employee = {leave.employee_id.id: leave for leave in existing}

            obsolete = existing.filtered(lambda lv: lv.employee_id.id not in target_employee_ids)
            if obsolete:
                obsolete.unlink()

            request_to = holiday.date_to or holiday.date_from
            private_name = f"Holiday: {holiday.name}"
            for employee in target_employees:
                leave = existing_by_employee.get(employee.id)
                vals = {
                    "employee_id": employee.id,
                    "holiday_status_id": leave_type.id,
                    "request_date_from": holiday.date_from,
                    "request_date_to": request_to,
                    "private_name": private_name,
                    "state": "validate",
                    "resonnocare_holiday_calendar_id": holiday.id,
                    "resonnocare_is_calendar_holiday": True,
                }
                if leave:
                    # Validated time-off records are state-protected in Odoo and
                    # cannot always be edited directly. Recreate safely.
                    leave.unlink()
                    leave_model.create(vals)
                else:
                    leave_model.create(vals)

    def _sync_resource_calendar_holidays(self):
        resource_leave_model = self.env["resource.calendar.leaves"].sudo().with_context(
            tracking_disable=True,
            mail_notrack=True,
            mail_create_nosubscribe=True,
        )
        for holiday in self:
            existing = resource_leave_model.search(
                [("resonnocare_holiday_calendar_id", "=", holiday.id)],
                limit=1,
            )
            if not holiday.active:
                if existing:
                    existing.unlink()
                continue

            start_dt = datetime.combine(holiday.date_from, time.min)
            end_date = holiday.date_to or holiday.date_from
            end_dt = datetime.combine(end_date, time.max)

            vals = {
                "name": holiday.name,
                "date_from": fields.Datetime.to_string(start_dt),
                "date_to": fields.Datetime.to_string(end_dt),
                "resource_id": False,
                "calendar_id": False,
                "company_id": self.env.company.id,
                "resonnocare_holiday_calendar_id": holiday.id,
            }
            if existing:
                existing.write(vals)
            else:
                resource_leave_model.create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_resource_calendar_holidays()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_resource_calendar_holidays()
        return result

    def unlink(self):
        self.env["resource.calendar.leaves"].sudo().search(
            [("resonnocare_holiday_calendar_id", "in", self.ids)]
        ).unlink()
        return super().unlink()

    def action_resync_timeoff_calendar(self):
        self.sudo()._sync_resource_calendar_holidays()
        return True


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    resonnocare_holiday_calendar_id = fields.Many2one(
        "resonnocare.holiday.calendar",
        string="Resonnocare Holiday",
        index=True,
        copy=False,
        ondelete="cascade",
    )
