# -*- coding: utf-8 -*-

from odoo import fields, models


class ResonnocareAudiometryResultMark(models.Model):
    _name = "resonnocare.audiometry.result.mark"
    _description = "Audiometry Test Result Mark"
    _order = "id asc"

    result_id = fields.Many2one(
        "resonnocare.audiometry.result",
        string="Result",
        required=True,
        ondelete="cascade",
        index=True,
    )
    ear = fields.Selection(
        [("left", "Left"), ("right", "Right")],
        string="Ear",
        required=True,
    )
    mode = fields.Selection(
        [("AC", "AC"), ("BC", "BC"), ("FF", "FF")],
        string="Mode",
        required=True,
    )
    masking = fields.Boolean(string="Masking")
    frequency = fields.Float(string="Frequency")
    intensity = fields.Float(string="Intensity")
    response = fields.Char(string="Response")
    transaction_date = fields.Char(string="Transaction Date")
    c1 = fields.Char(string="C1")
    c2 = fields.Char(string="C2")
    c3 = fields.Char(string="C3")
    c4 = fields.Char(string="C4")
    c5 = fields.Char(string="C5")
    c6 = fields.Char(string="C6")