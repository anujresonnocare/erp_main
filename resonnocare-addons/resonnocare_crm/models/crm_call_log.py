# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResonnocareCrmCallLog(models.Model):
    _name = "resonnocare.crm.call.log"
    _description = "Resonnocare CRM Call Log"
    _order = "call_datetime desc, id desc"

    name = fields.Char(
        string="Call Log ID",
        required=True,
        copy=False,
        default="New",
        readonly=True,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Agent",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    disposition_id = fields.Many2one(
        "resonnocare.crm.disposition",
        string="Disposition",
        required=True,
        ondelete="restrict",
    )
    attempt_number = fields.Integer(
        string="Attempt Number",
        required=True,
        readonly=True,
    )
    call_datetime = fields.Datetime(
        string="Call Time",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    lead_relevant = fields.Boolean(
        string="Lead Relevant",
        readonly=True,
    )
    next_followup_date = fields.Date(
        string="Next Follow-up",
        readonly=True,
    )
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = sequence.next_by_code("resonnocare.crm.call.log") or "New"
        return super().create(vals_list)
