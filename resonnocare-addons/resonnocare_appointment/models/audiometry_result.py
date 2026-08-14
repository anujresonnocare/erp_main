# -*- coding: utf-8 -*-

from odoo import fields, models


class ResonnocareAudiometryResult(models.Model):
    _name = "resonnocare.audiometry.result"
    _description = "Audiometry Test Result"
    _order = "id desc"

    uid = fields.Char(string="UID", required=True, index=True, copy=False)
    session_id = fields.Char(string="Session ID", required=True, index=True)
    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        required=True,
        ondelete="restrict",
        index=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        required=True,
        ondelete="restrict",
        index=True,
    )
    test_name = fields.Char(string="Test Name", required=True)
    created_at = fields.Char(string="Created At", required=True)
    clinical_impresion_left = fields.Text(string="Clinical Impression Left")
    clinical_impresion_right = fields.Text(string="Clinical Impression Right")
    recommendation = fields.Text(string="Recommendation")
    report_attachment_id = fields.Many2one(
        "ir.attachment",
        string="Report Attachment",
        ondelete="set null",
        copy=False,
    )
    mark_ids = fields.One2many(
        "resonnocare.audiometry.result.mark",
        "result_id",
        string="Result Marks",
    )