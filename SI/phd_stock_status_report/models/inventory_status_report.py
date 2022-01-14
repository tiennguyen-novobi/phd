# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo import api, fields, models, _
import math
import logging

_logger = logging.getLogger(__name__)


class InventoryStatusReportModel(models.Model):
    _name = "stock.status.report.line"
    _description = "Stock Status Report Line"
    _order = 'product_id'
    _rec_name = 'product_id'

    default_code = fields.Char(string='Internal Reference', related='product_id.default_code')
    name = fields.Char(string='Product Name', related='product_id.name')
    forecasted_demand_ok = fields.Boolean(string='Is forecasted?', related='product_id.forecasted_demand_ok')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    qty_available = fields.Float(string='On Hand', related='product_id.qty_available', digits='Product Unit of Measure')
    free_qty = fields.Float(string='Available', related='product_id.free_qty', digits='Product Unit of Measure')
    qty_reserved = fields.Float(string='Reserved', compute='_compute_qty_reserved_from_stock_quant',
                                digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    purchase_lead_time = fields.Integer(string='Purchase Lead Time', related='product_id.purchase_lead_time')
    safety_stock = fields.Float(string='Safety Stock', digits='Product Unit of Measure',
                                related='product_id.safety_stock')

    dynamical_forecasted_date = fields.Date(string='Dynamical Forecasted Date', store=False)
    forecasted_date = fields.Date(string='Forecasted Date')
    forecasted_demand = fields.Float(string='Forecasted Demand', digits='Product Unit of Measure',
                                     compute='_compute_quantity')
    recommended_order_qty = fields.Float(string='Recommended Order Qty', digits='Product Unit of Measure',
                                         compute='_compute_quantity', default=0)
    incoming_qty = fields.Float(string='Incoming Qty', digits='Product Unit of Measure',
                                compute='_compute_incoming_qty')
    remaining_qty = fields.Float(string='Remaining Qty', digits='Product Unit of Measure',
                                 compute='_compute_quantity')
    stock_status = fields.Selection(string='Status', selection=[('enough', 'Enough'), ('replenish', 'Replenish')],
                                    compute='_compute_stock_status', search='_search_stock_status')
    purchase_line_ids = fields.Many2many('purchase.order.line', string='Purchase Lines',
                                        compute='_compute_purchase_lines')
    last_date_to_replenish = fields.Date(string='Last Date to Replenish', compute='_compute_last_date_to_replenish')

    def default_get(self, fields):
        res = super(InventoryStatusReportModel, self).default_get(fields)
        if self:
            if 'dynamical_forecasted_date' not in res:
                today_user = datetime.now(timezone(self.env.user.tz or 'UTC')).date()
                if not self.forecasted_date or self.forecasted_date < today_user:
                    self.forecasted_date = today_user + relativedelta(days=self.purchase_lead_time)
                res['dynamical_forecasted_date'] = self.forecasted_date
        return res

    def write(self, values):
        if 'dynamical_forecasted_date' in values:
            values['forecasted_date'] = values['dynamical_forecasted_date']
        return super(InventoryStatusReportModel, self).write(values)

    def _compute_qty_reserved_from_stock_quant(self):
        product_ids = self.mapped('product_id').ids
        domain_loc = self.env['product.product']._get_domain_locations()[0]
        domain_loc.append(('product_id', 'in', product_ids))
        quant_ids = self.env['stock.quant'].search_read(domain_loc, ['id', 'product_id', 'reserved_quantity'],
                                                        order='product_id')
        oredered_records = self.sorted(lambda x: x['product_id'])
        index = 0
        length = len(quant_ids)
        for record in oredered_records:
            total_reserved = 0.0
            while index < length and record.product_id.id == quant_ids[index].get('product_id', 0)[0]:
                total_reserved += quant_ids[index].get('reserved_quantity', 0)
                index += 1
            record.qty_reserved = total_reserved

    @api.model
    def get_default_date_range(self, forecasted_datetime):
        user_time = datetime.now(timezone(self.env.user.tz or 'UTC'))
        return user_time.date(), forecasted_datetime

    @api.depends('remaining_qty')
    def _compute_stock_status(self):
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for record in self:
            record.stock_status = (
                    record.check_stock_status_situation(precision_digits) <= 0 and 'enough' or 'replenish')

    def check_stock_status_situation(self, precision_digits):
        start_date, end_date = self.get_default_date_range(self.forecasted_date)
        forecasted_demand = self.calculate_forecasted_demand(self.product_id.id, start_date, end_date)
        actual_remaining_qty = self.calculate_actual_remaining_qty(self.product_id.id, start_date, end_date,
                                                                   self.free_qty, forecasted_demand)
        return float_compare(self.product_id.safety_stock, actual_remaining_qty, precision_digits=precision_digits)

    def _search_stock_status(self, operator, operand):
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        domain = []
        if operator == '=':
            satisfy_ids = []
            record_set = self.search([])
            if operand == 'enough':
                satisfy_ids = record_set.filtered(
                    lambda record: record.check_stock_status_situation(precision_digits) <= 0).ids
            elif operand == 'replenish':
                satisfy_ids = record_set.filtered(
                    lambda record: record.check_stock_status_situation(precision_digits) > 0).ids
            domain = [('id', 'in', satisfy_ids)]
        return domain

    @api.depends('forecasted_date')
    def _compute_quantity(self):
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for record in self:
            if record.forecasted_date:
                start_date, end_date = self.get_default_date_range(record.forecasted_date)
                record.forecasted_demand = self.calculate_forecasted_demand(record.product_id.id, start_date, end_date)
                actual_remaining_qty = self.calculate_actual_remaining_qty(record.product_id.id, start_date, end_date,
                                                                           record.free_qty, record.forecasted_demand)
                record.remaining_qty = actual_remaining_qty if float_compare(actual_remaining_qty, 0,
                                                                             precision_digits=precision_digits) > 0 else 0
                minimum_order_qty = record.product_id.minimum_purchase_qty
                product_safety_stock = record.product_id.safety_stock
                if float_compare(actual_remaining_qty, product_safety_stock, precision_digits=precision_digits) >= 0:
                    record.recommended_order_qty = 0
                elif float_compare(minimum_order_qty, 0, precision_digits=precision_digits) > 0:
                    record.recommended_order_qty = math.ceil(
                        (product_safety_stock - actual_remaining_qty) / minimum_order_qty) * minimum_order_qty
                else:
                    record.recommended_order_qty = product_safety_stock - actual_remaining_qty
            else:
                record.forecasted_demand = 0
                record.remaining_qty = 0
                record.recommended_order_qty = 0

    def _compute_incoming_qty(self):
        for record in self:
            record.incoming_qty = self.calculate_incoming_qty(record.product_id.id)

    def _compute_purchase_lines(self):
        for record in self:
            purchase_line_ids = []
            if record.forecasted_date:
                purchase_ids = record.calculate_incoming_data(record.product_id.id, catch='purchase')
                purchase_line_ids = [(6, 0, purchase_ids)]
            record.purchase_line_ids = purchase_line_ids

    @api.depends('forecasted_date')
    def _compute_last_date_to_replenish(self):
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for record in self:
            safety_stock = record.product_id.safety_stock
            available_qty = record.free_qty
            if record.forecasted_date and record.stock_status == 'replenish':
                _logger.log(25,
                            "=======================================================================================")
                _logger.log(25,
                            "Calculate Last Date to Replenish for product id = {}, Safety Stock = {}, Available = {}".format(
                                record.product_id.id, safety_stock, available_qty))
                start_date, end_date = self.get_default_date_range(record.forecasted_date)
                date_range = (end_date - start_date).days + 1
                is_last_date_to_replenish_set = False
                for index in range(0, date_range):
                    running_date = start_date + relativedelta(days=index)
                    incoming_qty = self.calculate_incoming_qty(record.product_id.id, running_date, running_date)
                    demand_qty = self.calculate_forecasted_demand(record.product_id.id, running_date, running_date)
                    available_qty = available_qty + incoming_qty - demand_qty
                    _logger.log(25,
                                "Date {}, Incoming = {}, Demand = {}, Remaining = {}".format(running_date, incoming_qty,
                                                                                             demand_qty, available_qty))
                    if float_compare(available_qty, safety_stock, precision_digits=precision_digits) < 0:
                        last_date_to_replenish = running_date - relativedelta(days=record.product_id.purchase_lead_time)
                        if last_date_to_replenish < start_date:
                            last_date_to_replenish = start_date
                        record.last_date_to_replenish = last_date_to_replenish
                        is_last_date_to_replenish_set = True
                        _logger.log(25, "=> Available less than safety stock from {}".format(running_date))
                        _logger.log(25, "=> With product lead time = {} so the Last Date to Replenish is {}".format(
                            record.product_id.purchase_lead_time, last_date_to_replenish))
                        break
                if not is_last_date_to_replenish_set:
                    record.last_date_to_replenish = False
            else:
                record.last_date_to_replenish = False

    @api.model
    def calculate_forecasted_demand(self, product_id, start_date, end_date):
        margin_end_date = end_date + relativedelta(days=7)
        query_stmt = """
            SELECT week_end_date, SUM(demand_qty) as demand_qty
            FROM demand_forecast_item
            WHERE   week_end_date >= '{start_date}'::date 
                AND week_end_date < '{end_date}'::date
                AND product_id = {product_id}
            GROUP BY week_end_date
            ORDER BY week_end_date;    
        """.format(start_date=start_date, end_date=margin_end_date, product_id=product_id)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        forecasted_demand = 0.0
        if result:
            forecasted_demand = sum([x.get('demand_qty') for x in result])
            padding_start_days = result[0].get('week_end_date', start_date) - start_date
            forecasted_demand -= result[0].get('demand_qty', 0.0) * (6 - padding_start_days.days) / 7
            if end_date <= result[-1].get('week_end_date'):
                padding_end_days = result[-1].get('week_end_date', end_date) - end_date
                forecasted_demand -= result[-1].get('demand_qty', 0.0) * padding_end_days.days / 7

        return forecasted_demand

    @api.model
    def calculate_incoming_qty(self, product_id, start_date=False, end_date=False):
        return self.calculate_incoming_data(product_id, start_date, end_date)

    @api.model
    def calculate_incoming_data(self, product_id, start_date=False, end_date=False, catch='qty'):
        """
        Get incoming quantity based on condition
        :param product_id: The specific product_id that we want to fetch quantity
        :param start_date: optional param to finalize the start datetime boundary
        :param end_date: optional param to finalize the end datetime boundary
        :param catch: `qty` or `purchase` or `both`
        :return: {total qty} if catch == qty else {list id of purchase lines}
        """
        date_range_condition = ""
        if start_date and end_date:
            usertz = self.env.user.tz or 'UTC'
            date_range_condition = f"""AND (date_expected AT TIME ZONE '{usertz}')::date >= '{start_date}'::date 
                AND (date_expected AT TIME ZONE '{usertz}')::date <= '{end_date}'::date"""
        select_stmt = "sum(sm.product_uom_qty) as total"
        group_by_stmt = ""
        if catch == 'purchase':
            select_stmt = "ARRAY_AGG(pol.id) as purchase_line_ids"
        elif catch == 'both':
            select_stmt = "pol.id, sum(sm.product_uom_qty) as qty"
            group_by_stmt = "GROUP BY pol.id"
        query_stmt = """
            SELECT {select_stmt}
            FROM purchase_order_line as pol
            INNER JOIN 
             (SELECT purchase_line_id ,product_uom_qty, picking_id, date_expected 
                 FROM stock_move
                 WHERE state = 'assigned' AND product_id = {product_id} 
                {date_range_condition}
             ) as sm 
            ON sm.purchase_line_id = pol.id 
            INNER JOIN stock_picking sp  
            ON sm.picking_id = sp.id
            INNER JOIN (
                SELECT id, code, default_location_dest_id
                    FROM stock_picking_type
                    WHERE code = 'incoming'
                ) as spt
            ON spt.id = sp.picking_type_id
            INNER JOIN (
                SELECT usage, id FROM stock_location
                 WHERE usage NOT IN ('customer', 'transit')
                 ) as sl
            ON sl.id = spt.default_location_dest_id
            {group_by_stmt}
        """.format(select_stmt=select_stmt, group_by_stmt=group_by_stmt,
                   product_id=product_id, start_date=start_date, end_date=end_date,
                   date_range_condition=date_range_condition)
        self.env.cr.execute(query_stmt)
        if catch == 'both':
            return self.env.cr.dictfetchall()
        res = self.env.cr.dictfetchone()
        if catch == "purchase":
            return res and res.get('purchase_line_ids') or []

        return res and res.get('total', 0) or 0

    @api.model
    def calculate_actual_remaining_qty(self, product_id, start_date, end_date, free_qty=0.0, forecasted_demand=0.0):
        incoming_qty_in_range = self.calculate_incoming_qty(product_id, start_date, end_date)
        remaining_qty = free_qty + incoming_qty_in_range - forecasted_demand
        return remaining_qty

    def open_stock_status_record(self):
        self.ensure_one()
        return {
            'name': _(self.product_id.name),
            'view_mode': 'form',
            'res_model': 'stock.status.report.line',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }
