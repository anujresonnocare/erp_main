from odoo import models, fields, api


class ResonnocareHQDashboard(models.Model):
    _name = "resonnocare.hq.dashboard"
    _description = "Resonnocare HQ Dashboard"

    total_clinics = fields.Integer(
        compute="_compute_clinic_stats", string="Total Clinics"
    )
    active_clinics = fields.Integer(
        compute="_compute_clinic_stats", string="Active Clinics"
    )
    appointments_today = fields.Integer(
        compute="_compute_appointments_today", string="Appointments Today"
    )
    registrations_today = fields.Integer(
        compute="_compute_registrations_today", string="Registrations Today"
    )

    @api.depends()
    def _compute_clinic_stats(self):
        """Compute clinic statistics from resonnocare.clinic if available"""
        for record in self:
            # Check if resonnocare_clinic module is installed (model exists)
            if "resonnocare.clinic" in self.env:
                record.total_clinics = self.env["resonnocare.clinic"].search_count([])
                record.active_clinics = self.env["resonnocare.clinic"].search_count(
                    [("clinic_status", "=", "active")]
                )
            else:
                # If module not installed, no clinics exist
                record.total_clinics = 0
                record.active_clinics = 0

    @api.depends()
    def _compute_appointments_today(self):
        """Placeholder for when appointment module is implemented"""
        for record in self:
            record.appointments_today = 0

    @api.depends()
    def _compute_registrations_today(self):
        """Placeholder for when patient registration module is implemented"""
        for record in self:
            record.registrations_today = 0
