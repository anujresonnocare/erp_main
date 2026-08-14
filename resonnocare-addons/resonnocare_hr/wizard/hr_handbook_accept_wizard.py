import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request


class HrHandbookAcceptWizard(models.TransientModel):
    _name = "resonnocare.hr.handbook.accept.wizard"
    _description = "HR Handbook Acceptance Wizard"
    _rec_name = "employee_id"

    employee_id = fields.Many2one("hr.employee", readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    handbook_version_id = fields.Many2one("resonnocare.hr.handbook.version", readonly=True)
    handbook_content_html = fields.Html(readonly=True)
    accepted_already = fields.Boolean(readonly=True)
    accepted_on = fields.Datetime(readonly=True)
    accepted_ip = fields.Char(readonly=True)
    acknowledge = fields.Boolean(string="I have read and accept this HR Handbook")
    contract_required = fields.Boolean(readonly=True)
    contract_ready = fields.Boolean(readonly=True)

    @api.model
    def default_get(self, fields_list):
        # Keep one transient onboarding wizard record per user to avoid form pager arrows.
        self.sudo().search([("create_uid", "=", self.env.user.id)]).unlink()
        vals = super().default_get(fields_list)
        employee = self.env.user.employee_id
        has_contract_model = "hr.contract" in self.env
        vals.update(
            {
                "employee_id": employee.id,
                "user_id": self.env.user.id,
                "contract_required": has_contract_model,
            }
        )

        handbook = self.env["resonnocare.hr.handbook.version"].search([("state", "=", "published")], limit=1)
        if handbook:
            vals["handbook_version_id"] = handbook.id
            vals["handbook_content_html"] = handbook.content_html

        if employee:
            contract_ready = False
            if has_contract_model:
                contract_model = self.env["hr.contract"].sudo()
                contract_domain = [("employee_id", "=", employee.id), ("state", "=", "open")]
                if employee.user_id:
                    contract_domain = [
                        ("state", "=", "open"),
                        "|",
                        ("employee_id", "=", employee.id),
                        ("employee_id.user_id", "=", employee.user_id.id),
                    ]
                if "active" in contract_model._fields:
                    contract_ready = bool(
                        contract_model.with_context(active_test=False).search_count(contract_domain)
                    )
                else:
                    contract_ready = bool(contract_model.search_count(contract_domain))
                if not contract_ready and employee.resonnocare_employee_code:
                    code_domain = [
                        ("state", "=", "open"),
                        ("employee_id.resonnocare_employee_code", "=", employee.resonnocare_employee_code),
                    ]
                    if "active" in contract_model._fields:
                        contract_ready = bool(
                            contract_model.with_context(active_test=False).search_count(code_domain)
                        )
                    else:
                        contract_ready = bool(contract_model.search_count(code_domain))
                if not contract_ready and employee.name:
                    name_domain = [("state", "=", "open"), ("employee_id.name", "=", employee.name)]
                    if employee.company_id:
                        name_domain.append(("employee_id.company_id", "=", employee.company_id.id))
                    if "active" in contract_model._fields:
                        contract_ready = bool(
                            contract_model.with_context(active_test=False).search_count(name_domain)
                        )
                    else:
                        contract_ready = bool(contract_model.search_count(name_domain))
            vals["contract_ready"] = contract_ready

            if handbook:
                acceptance = self.env["resonnocare.hr.handbook.acceptance"].search(
                    [("employee_id", "=", employee.id), ("handbook_version_id", "=", handbook.id)],
                    limit=1,
                )
                if acceptance:
                    vals.update(
                        {
                            "accepted_already": True,
                            "accepted_on": acceptance.accepted_on,
                            "accepted_ip": acceptance.accepted_ip,
                        }
                    )
        return vals

    def _get_request_metadata(self):
        ip_addr = ""
        user_agent = ""
        if request and request.httprequest:
            forwarded_for = request.httprequest.headers.get("X-Forwarded-For")
            ip_addr = (forwarded_for.split(",")[0].strip() if forwarded_for else request.httprequest.remote_addr) or ""
            user_agent = request.httprequest.headers.get("User-Agent", "")
        return ip_addr, user_agent

    def _get_post_accept_action(self):
        profile_server_action = self.env.ref(
            "resonnocare_hr.action_open_resonnocare_my_profile_server",
            raise_if_not_found=False,
        )
        if profile_server_action:
            return {"type": "ir.actions.server", "id": profile_server_action.id}

        action = self.env.ref("resonnocare_hr.action_resonnocare_my_profile", raise_if_not_found=False)
        if action:
            action_vals = action.sudo().read()[0]
            action_vals["res_id"] = self.env.user.id
            context = dict(self.env.context or {})
            context.update(
                {
                    "from_my_profile": True,
                    "form_view_initial_mode": "edit",
                    "create": False,
                }
            )
            action_vals["context"] = context
            return action_vals
        return {"type": "ir.actions.act_url", "url": "/odoo", "target": "self"}

    def action_accept(self):
        self.ensure_one()

        if not self.employee_id:
            raise UserError(_("No employee is linked to your user. Please contact HR."))
        if not self.handbook_version_id:
            raise UserError(_("No published HR handbook is available. Please contact HR."))
        if not self.acknowledge:
            raise UserError(_("Please tick the acknowledgment checkbox to continue."))

        if self.contract_required and not self.contract_ready:
            raise UserError(
                _("Your payroll contract is not configured yet. Please contact HR before accepting onboarding.")
            )

        acceptance_env = self.env["resonnocare.hr.handbook.acceptance"].sudo()
        existing = acceptance_env.search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("handbook_version_id", "=", self.handbook_version_id.id),
            ],
            limit=1,
        )
        if existing:
            return self._get_post_accept_action()

        accepted_on = fields.Datetime.now()
        ip_addr, user_agent = self._get_request_metadata()

        acceptance = acceptance_env.create(
            {
                "employee_id": self.employee_id.id,
                "user_id": self.user_id.id,
                "handbook_version_id": self.handbook_version_id.id,
                "accepted_on": accepted_on,
                "accepted_ip": ip_addr,
                "accepted_user_agent": user_agent,
            }
        )

        evidence_text = (
            "HR HANDBOOK ACKNOWLEDGMENT\n"
            f"Employee ID: {self.employee_id.id}\n"
            f"Employee Name: {self.employee_id.name or ''}\n"
            f"Handbook Version: {self.handbook_version_id.version or ''}\n"
            f"Accepted On (UTC): {accepted_on}\n"
            f"Accepted IP: {ip_addr}\n"
            f"Accepted By User: {self.user_id.login or ''}\n"
        ).encode("utf-8")

        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": f"HR_Handbook_Acknowledgement_{self.handbook_version_id.version}.txt",
                "type": "binary",
                "datas": base64.b64encode(evidence_text),
                "res_model": "hr.employee",
                "res_id": self.employee_id.id,
                "mimetype": "text/plain",
            }
        )
        acceptance.employee_evidence_attachment_id = attachment.id

        action = self.env.ref("resonnocare_hr.action_hr_handbook_accept_wizard", raise_if_not_found=False)
        if action and self.user_id.action_id and self.user_id.action_id.id == action.id:
            self.user_id.sudo().write({"action_id": False})
        self.employee_id._sync_handbook_home_action()

        return self._get_post_accept_action()
