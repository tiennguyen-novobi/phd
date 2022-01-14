# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero

class PHDMrpProductProduce(models.TransientModel):
    _name = 'phd.mrp.add.qty.to.produce'

    raw_workorder_line_ids = fields.One2many('phd.mrp.add.qty.to.produce.line',
                                             'raw_product_produce_id', string='Components')

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',
                                    required=True, ondelete='cascade')

    @api.model
    def create(self, values):
        res = super(PHDMrpProductProduce, self).create(values)
        production = res.production_id
        if production.bom_id and production.bom_id.bom_line_ids:
            lines = production.bom_id.bom_line_ids
            for bom_line in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
                        bom_line.product_id.type not in ['product', 'consu']:
                    continue
                self.raw_workorder_line_ids.create({
                    'raw_product_produce_id': res.id,
                    'product_id': bom_line.product_id.id,
                    'quantity': 0,
                    'bom_line_id': bom_line.id,
                })
        return res

    def add_qty(self):
        self.ensure_one()
        raw_workorder_line_ids = self.raw_workorder_line_ids
        production = self.production_id
        if raw_workorder_line_ids and production:
            move_raw_ids = production.move_raw_ids
            for line in raw_workorder_line_ids:
                if not float_is_zero(line.quantity,precision_digits=0):
                    move_raw = move_raw_ids.filtered(lambda x: x.state not in ['done'] and x.product_id.id == line.product_id.id)
                    if move_raw:
                        move_raw[0].product_uom_qty += line.quantity
                    else:
                        line_data = {
                            'qty': line.quantity,
                            'product': line.product_id,
                            'parent_line': False,
                        }
                        move = production._get_move_raw_values(line.bom_line_id, line_data)
                        move_raw = self.env['stock.move'].create(move)
                        move_raw._adjust_procure_method()
                        (production.move_raw_ids | production.move_finished_ids)._action_confirm()
                        picking = production.purchase_id.picking_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
                        if picking:
                            move_lines = picking.move_lines.filtered(lambda x: x.product_id == production.product_id)
                            if move_lines:
                                finished_move = production.move_finished_ids.filtered(
                                    lambda m: m.product_id == move_lines[0].product_id)
                                finished_move.write({'move_dest_ids': [(4, move_lines[0].id, False)]})
                                production.move_raw_ids._action_assign()
                                production.workorder_ids._refresh_wo_lines()
        return {'type': 'ir.actions.act_window_close'}

class PHDMrpProductProduceLine(models.TransientModel):
    _name = 'phd.mrp.add.qty.to.produce.line'

    raw_product_produce_id = fields.Many2one('phd.mrp.add.qty.to.produce', 'Component in Produce wizard')
    product_id = fields.Many2one('product.product', string='Product')
    bom_line_id = fields.Many2one('mrp.bom.line', "Bill of Materials")
    quantity = fields.Float(string='Quantity')
    product_uom_id = fields.Many2one('uom.uom',related='product_id.uom_id', readonly=True)
