# -*- coding: utf-8 -*-
from odoo import models, fields


class ResonnocareCrmDisposition(models.Model):
    _name = "resonnocare.crm.disposition"
    _description = "CRM Call Disposition"
    _order = "sequence, id"
    _rec_name = "name"

    name = fields.Char(
        string="Disposition Name",
        required=True
    )

    rule_definition = fields.Text(
        string="Rule / Definition",
        help="Business rule or definition explaining when and how this disposition should be used."
    )

    follow_up_days = fields.Integer(
        string="Follow-up Days",
        default=0,
        help="Number of days after which follow-up should occur. 0 = no follow-up."
    )

    max_attempts = fields.Integer(
        string="Max Attempts",
        default=1,
        help="Maximum number of follow-up attempts before churn."
    )

    lead_relevant = fields.Boolean(
        string="Lead Relevant",
        default=True,
        help="If unchecked, lead is considered non-relevant."
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )
