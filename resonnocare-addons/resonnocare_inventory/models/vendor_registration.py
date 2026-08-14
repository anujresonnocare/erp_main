from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    # =========================
    # Vendor Identification
    # =========================
    vendor_code = fields.Char(string="Vendor Code")
    vendor_type = fields.Selection(
        [
            ("huf", "HUF"),
            ("sole", "Sole Proprietorship"),
            ("partnership", "Partnership"),
            ("private", "Private Company"),
        ],
        string="Vendor Type",
    )

    # =========================
    # Statutory / Tax Details
    # =========================
    pan_no = fields.Char(string="PAN Number")
    gst_no = fields.Char(string="GST Registration No")
    gst_type = fields.Selection(
        [
            ("regular", "Regular"),
            ("composition", "Composition"),
            ("unregistered", "Unregistered"),
        ],
        string="GST Registration Type",
    )
    msme_registered = fields.Boolean(string="MSME Registered")
    msme_no = fields.Char(string="MSME Number")

    # =========================
    # Bank Details
    # =========================
    bank_name = fields.Char(string="Bank Name")
    bank_branch = fields.Char(string="Branch")
    bank_account_no = fields.Char(string="Bank Account Number")
    ifsc_code = fields.Char(string="IFSC Code")
    account_type = fields.Selection(
        [
            ("saving", "Saving"),
            ("current", "Current"),
        ],
        string="Account Type",
    )

    # =========================
    # Payment / TDS Details
    # =========================
    payment_mode = fields.Selection(
        [
            ("rtgs", "RTGS"),
            ("neft", "NEFT"),
            ("cheque", "Cheque"),
        ],
        string="Preferred Payment Mode",
    )
    tds_applicable = fields.Boolean(string="TDS Applicable")
    tds_section = fields.Char(string="TDS Section")
    tds_exemption = fields.Boolean(string="TDS Exemption Certificate Available")

    # =========================
    # Contact Person (Extra)
    # =========================
    contact_person_name = fields.Char(string="Contact Person Name")
    contact_person_designation = fields.Char(string="Contact Person Designation")
    contact_person_mobile = fields.Char(string="Contact Person Mobile")
    contact_person_email = fields.Char(string="Contact Person Email")
