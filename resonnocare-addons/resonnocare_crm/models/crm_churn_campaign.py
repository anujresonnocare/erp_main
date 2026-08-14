# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResonnocareCrmChurnCampaign(models.Model):
    _name = "resonnocare.crm.churn.campaign"
    _description = "CRM Churn Campaign"
    _order = "churned_on desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Campaign ID",
        readonly=True,
        copy=False,
        default=lambda self: "New",
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Lead",
        required=True,
        ondelete="cascade",
        index=True,
    )
    assigned_agent_id = fields.Many2one(
        "res.users",
        string="Assigned Agent",
        readonly=True,
    )
    disposition_id = fields.Many2one(
        "resonnocare.crm.disposition",
        string="Disposition",
        readonly=True,
    )
    stage_id = fields.Many2one(
        "crm.stage",
        string="CRM Stage",
        readonly=True,
    )
    interested_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Interested Clinic",
        readonly=True,
    )
    preferred_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Preferred Clinic",
        readonly=True,
    )
    lead_source = fields.Selection(
        selection=lambda self: self.env["crm.lead"]._fields["x_lead_source"].selection,
        string="Lead Source",
        readonly=True,
    )
    lead_phone = fields.Char(string="Lead Phone", readonly=True)
    tenure_days = fields.Integer(string="Tenure (Days)", readonly=True)
    churned_on = fields.Datetime(string="Churned On", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="Campaign State",
        default="draft",
        required=True,
    )
    notes = fields.Text(string="Notes")

    _sql_constraints = [
        (
            "uniq_churn_campaign_per_lead",
            "unique(lead_id)",
            "A churn campaign already exists for this lead.",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "resonnocare.crm.churn.campaign"
                ) or "New"
        return super().create(vals_list)

    def action_mark_active(self):
        self.write({"state": "active"})

    def action_mark_closed(self):
        self.write({"state": "closed"})

    def action_mark_cancelled(self):
        self.write({"state": "cancelled"})
