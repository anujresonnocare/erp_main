from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class PatientSearchWizard(models.TransientModel):
    _name = "resonnocare.patient.search.wizard"
    _description = "Patient Search Wizard"

    search_term = fields.Char(string="Search (Phone / ID / Name)", required=True)
    warning_message = fields.Text(string="Warning", readonly=True)

    def action_open_registration(self):
        """Open the registration wizard manually."""
        search_term = self.search_term
        # If search term looks like a phone number, pre-fill it
        default_phone = False
        if search_term and search_term.isdigit() and len(search_term) >= 10:
            default_phone = search_term

        return {
            "type": "ir.actions.act_window",
            "name": _("Register New Patient"),
            "res_model": "resonnocare.patient.registration.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_phone": default_phone},
        }

    def action_search_patient(self):
        self.ensure_one()

        # Phone validation
        if self.search_term.isdigit() and len(self.search_term) < 10:
            return {
                "type": "ir.actions.act_window",
                "name": _("Search Patient"),
                "res_model": self._name,
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_search_term": self.search_term,
                    "default_warning_message": _("Invalid Phone Number. Please enter at least 10 digits.")
                },
            }

        domain = [
            "|",
            "|",
            "|",
            ("patient_id", "ilike", self.search_term),
            ("phone", "ilike", self.search_term),
            ("mobile", "ilike", self.search_term),
            ("name", "ilike", self.search_term),
            ("is_patient", "=", True),
            ("company_id", "=", self.env.company.id),
        ]

        patients = self.env["res.partner"].search(domain)

        if patients:
            action = self.env.ref("resonnocare_frontdesk.action_patient_search").sudo().read()[
                0
            ]
            action["domain"] = [("id", "in", patients.ids)]
            # Ensure edit mode is enabled when opening patient list
            if "context" not in action:
                action["context"] = {}
            if isinstance(action["context"], str):
                action["context"] = safe_eval(action["context"].strip())
            action["context"]["form_view_initial_mode"] = "edit"
            action["context"]["edit"] = True
            return action

        # Patient NOT found → Open NEW wizard instance with context
        return {
            "type": "ir.actions.act_window",
            "name": _("Search Patient"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_search_term": self.search_term,
                "default_warning_message": _("Patient not found. Please click 'Register New Patient' to proceed.")
            },
        }
