# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_round, float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    ###################################
    # ACTION
    ###################################
    is_done_before = fields.Boolean("Field to check if move was done but changed to another state")
    is_old = fields.Boolean("Use to check If it is old then do not allow update date")

    def _update_subcontract_order_qty(self, quantity):
        for move in self:
            quantity_change = quantity - move.product_uom_qty
            production = move.move_orig_ids.production_id
            #######################################
            # Override OOTB Function
            # Handle Quantity to Produce Change for Subcontracting from MO instead of Receipt
            ########################################

            # if production and not float_is_zero(quantity_change, precision_digits=2):
            #     self.env['change.production.qty'].with_context(skip_activity=True).create({
            #         'mo_id': production.id,
            #         'product_qty': production.product_uom_qty + quantity_change
            #     }).change_prod_qty()

    def _create_extra_move(self):
        """ If the quantity done on a move exceeds its quantity todo, this method will create an
        extra move attached to a (potentially split) move line. If the previous condition is not
        met, it'll return an empty recordset.

        The rationale for the creation of an extra move is the application of a potential push
        rule that will handle the extra quantities.
        """
        extra_move = self
        rounding = self.product_uom.rounding
        # moves created after the picking is assigned do not have `product_uom_qty`, but we shouldn't create extra moves for them
        if float_compare(self.quantity_done, self.product_uom_qty, precision_rounding=rounding) > 0:
            # create the extra moves
            extra_move_quantity = float_round(
                self.quantity_done - self.product_uom_qty,
                precision_rounding=rounding,
                rounding_method='HALF-UP')
            extra_move_vals = self._prepare_extra_move_vals(extra_move_quantity)
            extra_move = self.copy(default=extra_move_vals)

            #######################################
            # Override OOTB Function
            # Fixbug Add Interim Line to Journal Entry
            ########################################
            if extra_move and self.move_dest_ids and self.move_dest_ids[0].is_subcontract:
                extra_move.move_dest_ids = self.move_dest_ids

            merge_into_self = all(
                self[field] == extra_move[field] for field in self._prepare_merge_moves_distinct_fields())

            if merge_into_self and extra_move.picking_id:
                extra_move = extra_move._action_confirm(merge_into=self)
                return extra_move
            else:
                extra_move = extra_move._action_confirm()

            # link it to some move lines. We don't need to do it for move since they should be merged.
            if not merge_into_self or not extra_move.picking_id:
                for move_line in self.move_line_ids.filtered(lambda ml: ml.qty_done):
                    if float_compare(move_line.qty_done, extra_move_quantity, precision_rounding=rounding) <= 0:
                        # move this move line to our extra move
                        move_line.move_id = extra_move.id
                        extra_move_quantity -= move_line.qty_done
                    else:
                        # split this move line and assign the new part to our extra move
                        quantity_split = float_round(
                            move_line.qty_done - extra_move_quantity,
                            precision_rounding=self.product_uom.rounding,
                            rounding_method='UP')
                        move_line.qty_done = quantity_split
                        move_line.copy(
                            default={'move_id': extra_move.id, 'qty_done': extra_move_quantity, 'product_uom_qty': 0})
                        extra_move_quantity -= extra_move_quantity
                    if extra_move_quantity == 0.0:
                        break
        return extra_move | self

    def _prepare_common_svl_vals(self):
        res = super(StockMove, self)._prepare_common_svl_vals()
        royalty_description = False
        if self.product_id.is_royalty:
            if self.move_line_ids and 'description' in res:
                product_id = self.move_line_ids.production_id.product_id
                product_sku = '- %s' % product_id.default_code if product_id else ''
                lot_ids = self.move_line_ids.lot_produced_ids
                lot_name = '- %s' % lot_ids[0].name if lot_ids else ''
                royalty_description = '%s %s %s' % (res.get('description'), product_sku, lot_name)
        if royalty_description:
            res.update({'description': royalty_description})
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_update_date = fields.Boolean()

    def action_update_produce_date(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Produce Date',
            'res_model': 'phd.update.date',
            'target': 'new',
            'view_id': self.env.ref('phd_inventory.phd_update_date_form_view').id,
            'view_mode': 'form',
            'context': {
                'default_date_time': self.date if self.date else False,
                'default_res_id': self.id,
                'default_field': 'date',
                'default_is_update': True,
                'default_model': self._name,
                'default_update_action_name': 'update_date_model_related',
            }
        }

    def update_date_model_related(self, date, field):
        self.ensure_one()
        if isinstance(date, str):
            date = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        only_date = date.astimezone(timezone).date()
        # Finished Product
        self.move_id.write({field: date})
        self.write({field: date})
        finished_product_stock_valuation_ids = self.move_id.stock_valuation_layer_ids
        if finished_product_stock_valuation_ids:
            sql_query = """
                        UPDATE stock_valuation_layer SET create_date = '{date_time}' WHERE id {operator} {ids}
                    """.format(date_time=date,
                               ids=tuple([record_id for record_id in finished_product_stock_valuation_ids.ids]) if len(
                                   finished_product_stock_valuation_ids) >= 2 else finished_product_stock_valuation_ids.id,
                               operator='in' if len(finished_product_stock_valuation_ids) >= 2 else '=')
            self.env.cr.execute(sql_query, [])
            # Accounting
            finished_product_stock_valuation_ids.account_move_id.write({field: only_date})
            finished_product_stock_valuation_ids.account_move_id.invoice_line_ids.write({'date': only_date})

        # Consumables Product
        self.consume_line_ids.move_id.write({field: date})
        self.consume_line_ids.write({field: date})
        consumable_move_line_ids = self.consume_line_ids
        consumable_stock_valuation_ids = consumable_move_line_ids.move_id.stock_valuation_layer_ids
        if consumable_stock_valuation_ids:
            sql_query = """
                            UPDATE stock_valuation_layer SET create_date = '{date_time}' WHERE id {operator} {ids}
                        """.format(date_time=date,
                                   ids=tuple([record_id for record_id in
                                              consumable_stock_valuation_ids.ids]) if len(
                                       consumable_stock_valuation_ids) >= 2 else consumable_stock_valuation_ids.id,
                                   operator='in' if len(consumable_stock_valuation_ids) >= 2 else '=')
            self.env.cr.execute(sql_query, [])
            # Accounting
            consumable_stock_valuation_ids.account_move_id.write({field: only_date})
            consumable_stock_valuation_ids.account_move_id.invoice_line_ids.write({field: only_date})


