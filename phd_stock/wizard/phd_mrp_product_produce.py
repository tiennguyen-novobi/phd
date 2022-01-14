from odoo import fields, models
from odoo.tools.float_utils import float_is_zero

class PHDMrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'
    
    def _update_finished_move(self):
        res = super(PHDMrpProductProduce, self)._update_finished_move()
        for wizard in self:
            if wizard.production_id and wizard.production_id.purchase_id:
                picking_ids = wizard.production_id.purchase_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if picking_ids:
                    # if wizard.finished_lot_id:
                    #     wizard.finished_lot_id.lot_qty = wizard.qty_producing
                    move_line = picking_ids[0].move_line_ids_without_package.filtered(
                        lambda x: x.product_id == wizard.product_id and not x.lot_id)
                    if move_line:
                        if not move_line[0].lot_id:
                            move_line[0].lot_id = wizard.finished_lot_id
                            move_line[0].qty_done = wizard.qty_producing
                    else:
                        move_line_has_lot = picking_ids[0].move_line_ids_without_package.filtered(
                            lambda x: x.product_id == wizard.product_id and wizard.finished_lot_id == x.lot_id)
                        if move_line_has_lot:
                            move_line_has_lot[0].qty_done += wizard.qty_producing
                        else:
                            move_id = picking_ids[0].move_ids_without_package.filtered(
                                lambda x: x.product_id == wizard.product_id)
                            if move_id:
                                self.env['stock.move.line'].create({
                                    'picking_id': picking_ids[0].id,
                                    'product_id': wizard.product_id.id,
                                    'move_id': move_id.id,
                                    'location_id': move_id.location_id.id,
                                    'location_dest_id': move_id.location_dest_id.id,
                                    'lot_id': wizard.finished_lot_id and wizard.finished_lot_id.id,
                                    'qty_done': wizard.qty_producing,
                                    'product_uom_id': wizard.product_uom_id.id,
                                })
        return res