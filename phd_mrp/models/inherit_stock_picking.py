# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta

from odoo.addons.mrp_subcontracting.models.stock_picking import StockPicking as OriginalStockPicking

def action_done(self):
    res = super(OriginalStockPicking, self).action_done()
    productions = self.env['mrp.production']
    for picking in self:
        for move in picking.move_lines:
            if not move.is_subcontract:
                continue
            production = move.move_orig_ids.production_id
            if move._has_tracked_subcontract_components():
                # move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel')).move_line_ids.unlink()
                move_finished_ids = move.move_orig_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                # for ml in move.move_line_ids:
                #     ml.copy({
                #         'picking_id': False,
                #         'production_id': move_finished_ids.production_id.id,
                #         'move_id': move_finished_ids.id,
                #         'qty_done': ml.qty_done,
                #         'result_package_id': False,
                #         'location_id': move_finished_ids.location_id.id,
                #         'location_dest_id': move_finished_ids.location_dest_id.id,
                #     })
            else:
                if not production.qty_produced:
                    wizards_vals = []
                    for move_line in move.move_line_ids:
                        wizards_vals.append({
                            'production_id': production.id,
                            'qty_producing': move_line.qty_done,
                            'product_uom_id': move_line.product_uom_id.id,
                            'finished_lot_id': move_line.lot_id.id,
                            'consumption': 'strict',
                        })
                    wizards = self.env['mrp.product.produce'].with_context(default_production_id=production.id).create(wizards_vals)
                    wizards._generate_produce_lines()
                    wizards._record_production()
            productions |= production
        for subcontracted_production in productions:
            if subcontracted_production.state == 'progress':
                subcontracted_production.post_inventory()
            else:
                subcontracted_production.write({'state': 'done'})
            # # For concistency, set the date on production move before the date
            # # on picking. (Tracability report + Product Moves menu item)
            # minimum_date = min(picking.move_line_ids.mapped('date'))
            # production_moves = subcontracted_production.move_raw_ids | subcontracted_production.move_finished_ids
            # production_moves.write({'date': minimum_date - timedelta(seconds=1)})
            # production_moves.move_line_ids.write({'date': minimum_date - timedelta(seconds=1)})
    return res


OriginalStockPicking.action_done = action_done


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ###################################
    # SUBCONTRACT HELPERS
    ###################################

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        vals = super(StockPicking, self)._prepare_subcontract_mo_vals(subcontract_move, bom)

        # Get Subcontract Operation Type from Purchase Order and add Source Document
        purchase_order = subcontract_move.picking_id.purchase_id
        if purchase_order:
            vals['origin'] = purchase_order.name
            vals['purchase_id'] = purchase_order.id

            purchase_line_id = subcontract_move.purchase_line_id
            vals['purchase_line_id'] = purchase_line_id.id if purchase_line_id else False
            # Check if Subcontract Operation Type from Purchase Order exist, then assign source and destination from it
            # to MO
            subcontract_picking_type = purchase_order.subcontract_picking_type_id
            receipt_date = purchase_order.date_planned
            picking_type_id = subcontract_picking_type.id
            if picking_type_id:
                location_src_id = subcontract_picking_type.default_location_src_id.id
                location_dest_id = subcontract_picking_type.default_location_dest_id.id
                vals.update({
                    'picking_type_id': picking_type_id,
                    'date_planned_finished': receipt_date,
                    'location_src_id': location_src_id,
                    'location_dest_id': location_dest_id
                })

        return vals

    def _subcontracted_produce(self, subcontract_details):
        not_auto_assign = not self.env['ir.config_parameter'].sudo().get_param('phd_mrp.auto_reserve_subcontracting_mo')
        res = super(StockPicking, self.with_context(not_auto_assign=not_auto_assign))._subcontracted_produce(subcontract_details)

        return res
