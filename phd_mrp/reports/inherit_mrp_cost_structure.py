# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import float_is_zero


class MrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'
    _description = 'MRP Cost Structure Report'

    def get_lines(self, productions):
        res = super(MrpCostStructure, self).get_lines(productions)
        po_cost_by_product_id = {}
        for product in productions.mapped('product_id'):
            mos = productions.filtered(lambda m: m.product_id == product)
            po_cost = 0.0
            for m in mos:
                move_finished_ids = m.move_finished_ids.filtered(
                    lambda mo: mo.state == 'done' and mo.product_id == product)
                quantity_done = sum(move_finished_ids.mapped('product_qty'))
                dest_moves = move_finished_ids.mapped('move_dest_ids')
                if dest_moves and dest_moves[0].purchase_line_id:
                    subcontracting_cost = m.extra_cost * quantity_done
                    po_cost += subcontracting_cost

            po_cost_by_product_id[product] = po_cost

        res = list(map(lambda rec: dict(rec, **{'po_cost': po_cost_by_product_id[rec['product']]}),
                       res)) if po_cost_by_product_id else res

        return res
