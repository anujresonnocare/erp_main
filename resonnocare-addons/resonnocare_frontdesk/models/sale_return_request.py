from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class SaleReturnRequest(models.Model):
    _name = "resonnocare.sale.return.request"
    _description = "Sale Order Return Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", required=True, readonly=True)
    patient_id = fields.Many2one(related="sale_order_id.patient_id", string="Patient", store=True)
    clinic_id = fields.Many2one(related="sale_order_id.clinic_id", string="Clinic", store=True)
    
    reason = fields.Text(string="Reason for Return", required=True)
    courier_details = fields.Char(string="Courier Details", help="Courier dispatch details if returning goods to HO.")
    
    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted to Finance"),
        ("approved", "Approved by Finance"),
        ("under_cancellation", "Under Cancellation"),
        ("cancelled", "Cancelled"),
        ("pending_refund", "Pending Refund"),
        ("refund_completed", "Refund Completed"),
        ("rejected", "Rejected")
    ], string="Status", default="draft", tracking=True)

    picking_ids = fields.One2many("stock.picking", compute="_compute_picking_ids", string="Return Pickings")
    picking_count = fields.Integer(compute="_compute_picking_ids")
    
    credit_note_ids = fields.One2many("account.move", compute="_compute_credit_note_ids", string="Credit Notes")
    credit_note_count = fields.Integer(compute="_compute_credit_note_ids")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("resonnocare.sale.return.request") or "New"
        return super().create(vals_list)

    def _compute_picking_ids(self):
        for req in self:
            if req.sale_order_id:
                domain = [('group_id', '=', req.sale_order_id.procurement_group_id.id)]
                if req.sale_order_id.procurement_group_id:
                    pickings = self.env['stock.picking'].search(domain)
                    # Get incoming pickings or returns
                    req.picking_ids = pickings.filtered(lambda p: p.picking_type_id.code == 'incoming' or (p.location_dest_id.usage != 'customer' and p.location_id.usage == 'customer'))
                else:
                    req.picking_ids = self.env['stock.picking']
                req.picking_count = len(req.picking_ids)
            else:
                req.picking_ids = False
                req.picking_count = 0

    def _compute_credit_note_ids(self):
        for req in self:
            if req.sale_order_id:
                cns = req.sale_order_id.invoice_ids.filtered(lambda i: i.move_type == 'out_refund')
                req.credit_note_ids = cns
                req.credit_note_count = len(cns)
            else:
                req.credit_note_ids = False
                req.credit_note_count = 0

    def action_submit(self):
        for req in self:
            if req.state != "draft":
                continue
            req.state = "submitted"
            
    def action_approve(self):
        for req in self:
            if req.state != "submitted":
                raise ValidationError("Only submitted requests can be approved.")
            req.state = "approved"
            req._generate_return_picking()

    def action_reject(self):
        for req in self:
            if req.state != "submitted":
                raise ValidationError("Only submitted requests can be rejected.")
            req.state = "rejected"
            
    def action_set_under_cancellation(self):
        for req in self:
            if req.state not in ("approved", "pending_refund"):
                continue
            req.state = "under_cancellation"

    def action_set_cancelled(self):
        for req in self:
            if req.state not in ("under_cancellation", "approved"):
                continue
            req.state = "cancelled"
            if req.sale_order_id.state != 'cancel':
                req.sale_order_id.with_context(disable_cancel_warning=True)._action_cancel()

    def action_set_pending_refund(self):
        for req in self:
            if req.state not in ("cancelled", "under_cancellation", "approved"):
                continue
            req.state = "pending_refund"

    def action_set_refund_completed(self):
        for req in self:
            if req.state != "pending_refund":
                continue
            req.state = "refund_completed"

    def _generate_return_picking(self):
        for req in self:
            so = req.sale_order_id
            delivered_pickings = so.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_code == 'outgoing')
            if not delivered_pickings:
                continue
                
            latest_picking = delivered_pickings.sorted(key=lambda p: p.date_done, reverse=True)[0]
            
            ReturnWizard = self.env['stock.return.picking']
            return_wizard = ReturnWizard.with_context(
                active_id=latest_picking.id,
                active_ids=[latest_picking.id],
                active_model='stock.picking'
            ).create({
                'picking_id': latest_picking.id,
            })
            res = return_wizard.create_returns()
            
            if req.courier_details:
                new_picking_id = res.get('res_id')
                if new_picking_id:
                    self.env['stock.picking'].browse(new_picking_id).write({
                        'note': f"Courier Details: {req.courier_details}"
                    })

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Pickings',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }

    def action_view_credit_notes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Notes',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.credit_note_ids.ids)],
        }
