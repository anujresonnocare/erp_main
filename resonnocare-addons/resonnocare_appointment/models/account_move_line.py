from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    serial_numbers = fields.Char(
        string="Serial Numbers",
        compute="_compute_serial_numbers",
        store=False,
    )

    @api.depends("sale_line_ids.move_ids.move_line_ids.lot_id", "product_id.item_type")
    def _compute_serial_numbers(self):
        for line in self:
            # Only show serial numbers for HA (Hearing Aid) and Charger (Equipment) products
            if line.product_id.item_type not in ('ha', 'equipment'):
                line.serial_numbers = False
                continue
            
            lots = line.sale_line_ids.mapped("move_ids.move_line_ids.lot_id")
            names = [name for name in lots.mapped("name") if name]
            line.serial_numbers = ", ".join(dict.fromkeys(names)) if names else False
