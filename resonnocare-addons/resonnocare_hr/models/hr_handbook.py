import base64
import csv
from io import StringIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResonnocareHrHandbookVersion(models.Model):
    _name = "resonnocare.hr.handbook.version"
    _description = "HR Handbook Version"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "effective_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    version = fields.Char(required=True, tracking=True)
    effective_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    content_html = fields.Html(required=True)
    state = fields.Selection(
        [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
        default="draft",
        required=True,
        tracking=True,
    )
    published_on = fields.Datetime(readonly=True, tracking=True)
    published_by = fields.Many2one("res.users", readonly=True, tracking=True)
    acceptance_ids = fields.One2many(
        "resonnocare.hr.handbook.acceptance",
        "handbook_version_id",
        string="Acceptances",
    )
    acceptance_count = fields.Integer(compute="_compute_acceptance_count")

    _sql_constraints = [
        ("resonnocare_hr_handbook_version_unique", "unique(version)", "Handbook version must be unique."),
    ]

    @api.depends("acceptance_ids")
    def _compute_acceptance_count(self):
        for record in self:
            record.acceptance_count = len(record.acceptance_ids)

    @api.constrains("state")
    def _check_single_published(self):
        for record in self.filtered(lambda r: r.state == "published"):
            published_count = self.search_count([("state", "=", "published"), ("id", "!=", record.id)])
            if published_count:
                raise ValidationError(_("Only one HR handbook can be published at a time."))

    def action_publish(self):
        self.ensure_one()
        archived = self.search([("state", "=", "published"), ("id", "!=", self.id)])
        archived.write({"state": "archived"})
        self.write(
            {
                "state": "published",
                "published_on": fields.Datetime.now(),
                "published_by": self.env.user.id,
            }
        )
        self.env["hr.employee"].search([("user_id", "!=", False)])._sync_handbook_home_action()

    def action_set_draft(self):
        for record in self:
            if record.acceptance_count:
                raise UserError(
                    _("Cannot move to Draft because employees have already accepted this handbook version.")
                )
            record.state = "draft"
        self.env["hr.employee"].search([("user_id", "!=", False)])._sync_handbook_home_action()

    def write(self, vals):
        protected_fields = {"content_html", "version", "effective_date"}
        for record in self:
            if protected_fields.intersection(vals.keys()) and (record.state == "published" or record.acceptance_count):
                raise UserError(
                    _("Published/accepted handbook versions are immutable. Create a new version instead.")
                )
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.acceptance_count or record.state == "published":
                raise UserError(_("Cannot delete a published/accepted handbook version."))
        return super().unlink()

    def action_download_acceptance_log(self):
        self.ensure_one()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Employee Database ID",
                "Employee Name",
                "Employee Work Email",
                "Handbook Version",
                "Accepted On (UTC)",
                "Accepted IP",
                "User",
            ]
        )

        for acceptance in self.acceptance_ids.sorted(key=lambda r: (r.accepted_on or fields.Datetime.now(), r.id)):
            writer.writerow(
                [
                    acceptance.employee_id.id,
                    acceptance.employee_id.name or "",
                    acceptance.employee_id.work_email or "",
                    acceptance.handbook_version_id.version or "",
                    acceptance.accepted_on or "",
                    acceptance.accepted_ip or "",
                    acceptance.user_id.login or "",
                ]
            )

        csv_data = output.getvalue().encode("utf-8")
        output.close()

        attachment = self.env["ir.attachment"].create(
            {
                "name": f"hr_handbook_acceptance_log_{self.version}.csv",
                "type": "binary",
                "datas": base64.b64encode(csv_data),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "text/csv",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


class ResonnocareHrHandbookAcceptance(models.Model):
    _name = "resonnocare.hr.handbook.acceptance"
    _description = "HR Handbook Acceptance"
    _order = "accepted_on desc, id desc"

    employee_id = fields.Many2one("hr.employee", required=True, index=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    handbook_version_id = fields.Many2one(
        "resonnocare.hr.handbook.version",
        required=True,
        ondelete="restrict",
    )
    accepted_on = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    accepted_ip = fields.Char(readonly=True)
    accepted_user_agent = fields.Char(readonly=True)
    employee_evidence_attachment_id = fields.Many2one("ir.attachment", readonly=True)

    _sql_constraints = [
        (
            "resonnocare_hr_handbook_accept_unique",
            "unique(employee_id, handbook_version_id)",
            "Employee has already accepted this handbook version.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("employee_id")._sync_handbook_home_action()
        return records
