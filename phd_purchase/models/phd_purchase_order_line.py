import logging

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class PHDPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    order_date_approve = fields.Datetime(string='PO Date',related='order_id.date_approve', store=True)
    # vendor_name = fields.Char(string='Vendor Name',related='partner_id.name')
    product_sku = fields.Char(string='SKU',related='product_id.default_code', store=True)
    lot_id = fields.Many2one('stock.production.lot', string='Lot#', store=True)
    receipt_id = fields.Many2one('stock.picking', string='Receipt#', store=True)
    receipt_date = fields.Datetime(string='Receipt Date')
    qty_receiving = fields.Float(string='Quantity', compute='_compute_po_receiving', default=0, store=True)

    @api.depends('move_ids','move_ids.state',
                 'move_ids.date_expected',
                 'move_ids.move_line_ids.lot_id')

    def _compute_po_receiving(self):
        for line in self:
            move_ids = line.move_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
            if move_ids:
                if line.move_ids[0].move_line_ids and line.move_ids[0].move_line_ids[0].lot_id:
                    line.lot_id = line.move_ids[0].move_line_ids[0].lot_id
                else:
                    line.lot_id = False
                line.receipt_id = line.move_ids[0].picking_id
                line.receipt_date = line.move_ids[0].date_expected
                line.qty_receiving = line.move_ids[0].product_uom_qty
            else:
                line.qty_receiving = 0