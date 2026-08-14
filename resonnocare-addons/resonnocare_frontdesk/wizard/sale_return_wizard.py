from odoo import models, fields, api

class SaleReturnWizard(models.TransientModel):
    _name = "resonnocare.sale.return.wizard"
    _description = "Wizard to Initiate Sale Return"

    sale_order_id = fields.Many2one("sale.order", string="Sale Order", required=True)
    reason = fields.Text(string="Reason for Return", required=True)
    courier_details = fields.Char(string="Courier Details", help="Enter courier tracking details if returning to HO.")
    
    def action_initiate_return(self):
        self.ensure_one()
        return_req = self.env["resonnocare.sale.return.request"].create({
            "sale_order_id": self.sale_order_id.id,
            "reason": self.reason,
            "courier_details": self.courier_details,
        })
        
        # Link request to the sale order (if we added a field on SO, though we can just compute it)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Request',
            'view_mode': 'form',
            'res_model': 'resonnocare.sale.return.request',
            'res_id': return_req.id,
            'target': 'current',
        }
