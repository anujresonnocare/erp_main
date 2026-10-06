from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    gstin = fields.Char(
        string='GSTIN',
        size=15,
        index=True,
        help='GSTIN registered for this state, if available in the supplied list.',
    )

    gst_state_hq = fields.Text(
        string='GST State HQ / Address',
        help='State headquarters or GST registration address from the supplied list.',
    )

    # _sql_constraints = [
    #     (
    #         'gst_state_name_country_unique',
    #         'unique(country_id, gst_state_name)',
    #         'The GST state name must be unique within a country.',
    #     ),
    # ]
