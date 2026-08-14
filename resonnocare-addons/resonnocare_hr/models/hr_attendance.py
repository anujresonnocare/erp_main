import math

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    check_in_latitude = fields.Float(string="Check-in Latitude", digits=(10, 7))
    check_in_longitude = fields.Float(string="Check-in Longitude", digits=(10, 7))
    check_out_latitude = fields.Float(string="Check-out Latitude", digits=(10, 7))
    check_out_longitude = fields.Float(string="Check-out Longitude", digits=(10, 7))

    attendance_profile_at_punch = fields.Selection([
        ('fixed', 'Fixed'),
        ('roaming', 'Roaming')
    ], string="Attendance Profile at Punch", readonly=True)
    resonnocare_punch_source = fields.Selection(
        [
            ("actual", "Actual"),
            ("regularized", "Regularized"),
        ],
        string="Punch Source",
        default="actual",
        readonly=True,
        copy=False,
    )
    resonnocare_check_in_regularized = fields.Boolean(
        string="Check-In Regularized",
        readonly=True,
        copy=False,
    )
    resonnocare_check_out_regularized = fields.Boolean(
        string="Check-Out Regularized",
        readonly=True,
        copy=False,
    )
    resonnocare_regularization_id = fields.Many2one(
        "resonnocare.attendance.regularization",
        string="Regularization Request",
        readonly=True,
        copy=False,
    )
    resonnocare_regularized_by = fields.Many2one(
        "res.users",
        string="Regularized By",
        readonly=True,
        copy=False,
    )
    resonnocare_regularized_on = fields.Datetime(
        string="Regularized On",
        readonly=True,
        copy=False,
    )

    def _is_hr_actor(self):
        user = self.env.user
        return (
            user.has_group("resonnocare_base.group_resonnocare_hr")
            or user.has_group("resonnocare_base.group_resonnocare_super_admin")
            or user.has_group("hr.group_hr_user")
        )

    @api.model
    def _get_geofence_radius_meters(self):
        """Default radius is 200m; override via system parameter if needed."""
        value = self.env["ir.config_parameter"].sudo().get_param(
            "resonnocare_hr.geofence_radius_meters",
            default="200",
        )
        try:
            radius = float(value)
        except (TypeError, ValueError):
            radius = 200.0
        return max(radius, 1.0)

    @api.model
    def _distance_meters(self, lat1, lon1, lat2, lon2):
        # Haversine distance
        earth_radius = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        return 2 * earth_radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _validate_geofence(self, employee, latitude, longitude, punch_type):
        """Enforce clinic geofence for fixed-profile employees."""
        if not employee or employee.attendance_profile != "fixed":
            return

        if not employee.clinic_id:
            raise ValidationError(
                _(
                    "Employee '%(employee)s' is Fixed profile but has no clinic assigned. "
                    "Please configure clinic before %(punch)s punch.",
                    employee=employee.name,
                    punch=punch_type,
                )
            )

        clinic = employee.clinic_id
        if clinic.clinic_latitude in (False, None) or clinic.clinic_longitude in (False, None):
            raise ValidationError(
                _(
                    "Clinic '%(clinic)s' does not have geo-location configured. "
                    "Please set clinic latitude/longitude before %(punch)s punch.",
                    clinic=clinic.name,
                    punch=punch_type,
                )
            )

        if latitude in (False, None) or longitude in (False, None):
            # Allow HR/manual corrections without geo payload.
            if self._is_hr_actor():
                return
            raise ValidationError(
                _(
                    "Location is required for %(punch)s punch for fixed-profile employees.",
                    punch=punch_type,
                )
            )

        distance = self._distance_meters(
            latitude,
            longitude,
            clinic.clinic_latitude,
            clinic.clinic_longitude,
        )
        radius = self._get_geofence_radius_meters()
        if distance > radius:
            raise ValidationError(
                _(
                    "You are outside clinic geofence for %(punch)s punch. "
                    "Distance: %(distance).1f m, allowed radius: %(radius).1f m.",
                    punch=punch_type,
                    distance=distance,
                    radius=radius,
                )
            )

    def write(self, vals):
        # Store profile snapshot and validate geofence on location updates.
        for attendance in self:
            if not attendance.attendance_profile_at_punch and attendance.employee_id.attendance_profile:
                vals['attendance_profile_at_punch'] = attendance.employee_id.attendance_profile

            employee = self.env["hr.employee"].browse(
                vals.get("employee_id", attendance.employee_id.id)
            )
            in_lat = vals.get("check_in_latitude", attendance.check_in_latitude)
            in_lon = vals.get("check_in_longitude", attendance.check_in_longitude)
            out_lat = vals.get("check_out_latitude", attendance.check_out_latitude)
            out_lon = vals.get("check_out_longitude", attendance.check_out_longitude)

            if any(key in vals for key in ("check_in", "check_in_latitude", "check_in_longitude")):
                self._validate_geofence(employee, in_lat, in_lon, "check-in")
            if any(key in vals for key in ("check_out", "check_out_latitude", "check_out_longitude")):
                self._validate_geofence(employee, out_lat, out_lon, "check-out")
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'employee_id' in vals:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.attendance_profile:
                    vals['attendance_profile_at_punch'] = employee.attendance_profile
                self._validate_geofence(
                    employee,
                    vals.get("check_in_latitude"),
                    vals.get("check_in_longitude"),
                    "check-in",
                )
                if vals.get("check_out") or vals.get("check_out_latitude") or vals.get("check_out_longitude"):
                    self._validate_geofence(
                        employee,
                        vals.get("check_out_latitude"),
                        vals.get("check_out_longitude"),
                        "check-out",
                    )
        return super().create(vals_list)
