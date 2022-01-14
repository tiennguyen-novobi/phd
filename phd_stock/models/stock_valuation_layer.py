from odoo import models, fields, api, _


class PHDStockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    stock_move_line_ids = fields.One2many('stock.move.line', related='stock_move_id.move_line_ids')

    lot_ids = fields.Many2many('stock.production.lot', compute='_compute_lot_id')
    location_id = fields.Many2one('stock.location', related='stock_move_id.location_id', store=True)
    dest_location_id = fields.Many2one('stock.location', related='stock_move_id.location_dest_id', store=True)

    @api.depends('stock_move_line_ids', 'stock_move_line_ids.lot_id')
    def _compute_lot_id(self):
        for record in self:
            if record.stock_move_line_ids:
                record.lot_ids = record.mapped('stock_move_line_ids.lot_id')
            else:
                record.lot_ids = False
