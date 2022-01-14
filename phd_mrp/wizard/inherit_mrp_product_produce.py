# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo.tools import float_compare

PRODUCT_STORABLE_TYPE = 'product'


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('raw_workorder_line_ids')
    def _onchange_raw_workorder_line_ids(self):
        self._update_available_quantity()

    ###################################
    # HELPERS FUNCTIONS
    ###################################
    def _update_available_quantity(self):
        stock_quant_env = self.env['stock.quant']

        # Key = (product_id, lot_id, location_id)
        qty_available_buffer = {}
        # Store last workorder line to add all remaining availabe quantity after distribution
        last_workorder_line_buffer = {}

        move_raw_ids = self.move_raw_ids

        location_id = self.production_id.location_src_id

        for line in self.raw_workorder_line_ids:
            if line.product_id.type == PRODUCT_STORABLE_TYPE:
                key = (line.product_id, line.lot_id, line.move_id.location_id)
                last_workorder_line_buffer[key] = line

                qty_available = qty_available_buffer.get(key)
                if qty_available is None:
                    # Available quantity = quantity on hand (check on (product, lot, location))
                    qty_available = stock_quant_env._get_on_hand_quantity(line.product_id,
                                                                          location_id,
                                                                          lot_id=line.lot_id,
                                                                          strict=True)

                    qty_available_buffer[key] = qty_available

                # Distribute available quantity to workorder line
                # if availalble qty > reserved qty then use reserved quantity
                qty_available = min(line.qty_reserved, qty_available)
                line.qty_available = qty_available
                qty_available_buffer[key] -= qty_available

        # Add remaining available quantity to last line after distribution
        for key, line in last_workorder_line_buffer.items():
            remaining_available_qty = qty_available_buffer[key]
            if remaining_available_qty:
                line.qty_available += remaining_available_qty

    def _record_production(self):
        # Raise error if consumed qty is greater then reserved quantity
        component_consume_more_than_reserve_display_names = []
        for line in self._workorder_line_ids():
            if line._is_overconsume():
                component_consume_more_than_reserve_display_names.append(line.product_id.display_name)

        if component_consume_more_than_reserve_display_names:
            raise UserError(
                _(('It is not possible to consume more than available quantity of following component(s):\n- %s')
                  % '\n- '.join(component_consume_more_than_reserve_display_names)))
        res = super(MrpProductProduce, self)._record_production()
        return res

    def do_produce(self):
        """
        Post inventory after producing
        :return: Produce action
        """
        context = self.env.context.copy()
        context.update({
            'default_mrp_product_produce_id': self.id,
            'default_extra_cost': self.production_id.extra_cost
        })
        if not context.get('is_confirm', False):
            return {
                'type': 'ir.actions.act_window',
                'name': 'PHD Produce Confirmation',
                'res_model': 'phd.produce.confirmation',
                'view_mode': 'form',
                'target': 'new',
                'context': context
            }
        else:
            res = super(MrpProductProduce, self).do_produce()
            self.production_id.post_inventory()
            if self.default_date_time:
                moves_to_finish = self.production_id.move_finished_ids.filtered(lambda x: not x.is_old and x.state == 'done')
                for move in moves_to_finish:
                    for line in move.mapped('move_line_ids'):
                        line.update_date_model_related(self.default_date_time, 'date')
                    move.is_old = True
            return res


class MrpProductProduceLine(models.TransientModel):
    _inherit = 'mrp.product.produce.line'

    ###################################
    # FIELDS
    ###################################
    qty_available = fields.Float('Available', digits='Product Unit of Measure')

    ###################################
    # ONCHANGE FUNCTIONS
    ###################################
    @api.onchange('qty_done')
    def _onchange_workoder_line_ids(self):
        if self._is_overconsume():
            raise UserError(_(('It is not possible to consume more than available quantity of %s')
                              % self.product_id.display_name))

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def _is_overconsume(self):
        is_overconsume = self.qty_done > self.qty_available and self.product_id.type == PRODUCT_STORABLE_TYPE
        return is_overconsume
