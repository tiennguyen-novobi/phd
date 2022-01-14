# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.addons.phd_inventory.models.inherit_stock_picking import PICKING_TYPE_OUTGOING_CODE
from odoo import tools
from datetime import datetime
from dateutil import relativedelta
import operator as op
from odoo.tools import float_is_zero
import logging

_logger = logging.getLogger(__name__)

NUM_OF_MONTH_IN_YEAR = 12


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    lot_name_for_delivery = fields.Char(store=True)
    ###################################
    # FIELDS
    ###################################

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    lot_qty_on_location = fields.Float(string='Quantity', compute='_compute_lot_qty_on_location')

    def _compute_lot_qty_on_location(self):
        move_id = self._context.get('move_id')
        move_id = self.env['stock.move'].browse(move_id)
        location = move_id.location_id
        for record in self:
            quants = record.quant_ids.filtered(
                lambda q: q.location_id.usage in ['internal', 'transit'] and q.location_id == location)
            if quants:
                record.lot_qty_on_location = sum(quants.mapped('quantity'))
            else:
                record.lot_qty_on_location = record.product_qty

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        picking_id = self._context.get('active_picking_id')
        picking_id = self.env['stock.picking'].browse(picking_id)
        picking_type_code = picking_id.picking_type_id.code

        if picking_id and picking_type_code == PICKING_TYPE_OUTGOING_CODE:
            product_id = self._context.get('default_product_id')
            partner_id = picking_id.partner_id

            args = list(args or [])
            if not self._rec_name:
                _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
            elif not (name == '' and operator == 'ilike'):
                args += [(self._rec_name, operator, name)]
            lot_ids = self._search(args, limit=100, access_rights_uid=name_get_uid, order='use_date ASC')
            lot_ids = self.browse(lot_ids).with_user(name_get_uid)

            is_check_previous_shipment_date = self.get_is_check_previous_shipment_date(partner_id)
            expire_date_of_previous_shipment = is_check_previous_shipment_date \
                                               and self.get_expire_date_of_previous_shipment(product_id, partner_id.id)
            if expire_date_of_previous_shipment:
                # Filter all lots which use date >= expire date of previous shipment
                lot_ids = lot_ids.filtered(
                    lambda rec: rec.use_date and rec.use_date >= expire_date_of_previous_shipment)

            # Get shelf-life require of partner, if it not set then get from parent company
            required_shelf_life = self.get_required_shelf_life(partner_id)
            if required_shelf_life:
                # filter lots which use_date - now >= shelf-life require
                lot_ids = lot_ids.filtered(
                    lambda rec: self.get_number_of_month_between_date(rec.use_date,
                                                                      datetime.now()) >= required_shelf_life)
            lot_ids = lot_ids.recommend_lot_ids()
            names = tools.lazy(lambda: dict(lot_ids.recommend_lot_name_get()))
            return [(rid, tools.lazy(op.getitem, names, rid)) for rid in lot_ids.ids]
        else:
            res = super(StockProductionLot, self)._name_search(name=name, args=args, operator=operator, limit=100,
                                                               name_get_uid=name_get_uid)
        return res

    def recommend_lot_name_get(self):
        res = []
        for record in self:
            res.append((record.id, record.lot_name_for_delivery))
        return res

    def recommend_lot_ids(self):
        lot_ids = []
        # res = []
        move_id = self._context.get('move_id')
        move_id = self.env['stock.move'].browse(move_id)
        location = move_id.location_id

        for record in self:
            use_date = fields.Date.to_date(record.use_date) if record.use_date else 'Not set'
            quants = record.quant_ids.filtered(
                lambda q: q.location_id.usage in ['internal', 'transit'] and q.location_id == location)
            lot_product_qty = sum(quants.mapped('quantity'))

            record.lot_name_for_delivery = '%s Qty: %s Expiration: %s' % (record.name, lot_product_qty, use_date)
            if not float_is_zero(lot_product_qty, precision_digits=0):
                # res.append((record.id, name))
                lot_ids.append(record.id)
        return self.browse(lot_ids)

    ###################################
    # HELPER FUNCTIONS
    ###################################

    def get_number_of_month_between_date(self, date_start, date_end):
        relative = relativedelta.relativedelta(date_start, date_end)

        number_of_month = relative.years * NUM_OF_MONTH_IN_YEAR + relative.months

        return number_of_month

    def get_required_shelf_life(self, partner_obj):
        """
        Get parent required shelf life
        :param partner_obj:
        :type partner_obj: object
        :return:
        :rtype:
        """
        required_shelf_life = partner_obj.month_of_shelf_life_require
        partner = partner_obj
        while partner.parent_id and not required_shelf_life:
            partner = partner.parent_id
            required_shelf_life = partner.month_of_shelf_life_require

        return required_shelf_life

    def get_is_check_previous_shipment_date(self, partner_obj):
        """
        Get parent is check previous shipment date
        :param partner_obj:
        :type partner_obj: object
        :return:
        :rtype:
        """
        is_check_previous_shipment_date = partner_obj.check_previous_shipment_date
        partner = partner_obj
        while partner.parent_id and not is_check_previous_shipment_date:
            partner = partner.parent_id
            is_check_previous_shipment_date = partner.check_previous_shipment_date

        return is_check_previous_shipment_date

    def get_expire_date_of_previous_shipment(self, product_id, partner_id):
        """
        Get previous shipment expiration date of product for specific vendor
        :param product_id:
        :type product_id: int
        :param partner_id:
        :type partner_id: int
        :return:
        :rtype: datetime
        """
        sql_query = """
                       SELECT stock_production_lot.use_date AS previous_move_expire_date 
                       FROM stock_move
                       JOIN stock_move_line on stock_move.id = stock_move_line.move_id
                                       AND stock_move.product_id = %s
                                       AND stock_move.picking_id IS NOT NULL
                                       AND stock_move.state = %s
                       JOIN stock_production_lot ON stock_move_line.lot_id = stock_production_lot.id
                       JOIN stock_picking ON stock_picking.id = stock_move.picking_id 
                                        AND stock_picking.partner_id = %s
                       ORDER BY stock_move.date DESC,
                                stock_production_lot.use_date DESC
                       LIMIT 1;
                   """
        sql_params = [product_id, 'done', partner_id]
        self.env.cr.execute(sql_query, sql_params)
        result = self.env.cr.dictfetchall()
        use_date = result[0].get('previous_move_expire_date') if result else None
        return use_date
