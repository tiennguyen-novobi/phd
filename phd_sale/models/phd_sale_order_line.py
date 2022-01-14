from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_is_zero, float_compare
import random
from datetime import datetime
from datetime import date as dt

class PHDSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sales_order_date = fields.Datetime(related='order_id.date_order',string='SO Date', store=True)
    customer_po = fields.Char(related='order_id.client_order_ref', string='Customer PO', store=True)
    order_number = fields.Char(related='order_id.name', string='SO Number',store=True)
    date_ship = fields.Datetime(related='order_id.commitment_date', string='Ship Date',store=True)
    product_sku = fields.Char(related='product_id.default_code', string='SKU',store=True)
    product_category = fields.Char(related='product_id.categ_id.name',store=True, string='Category')
    is_unbilled_sales = fields.Boolean(compute='_compute_unbilled_sales',store=True)
    trigger_field = fields.Integer(compute='_compute_trigger_field')
    expected_delivery_date = fields.Datetime(store=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot#',
                             domain="[('product_id', '=', product_id)]")
    default_code = fields.Char(related="product_id.default_code")

    qty_backordered = fields.Float(string="Quantity Backordered", compute="_compute_backorder", store=True)
    days_late = fields.Integer(string="Days Late", compute="_compute_backorder", store=True)
    total_qty_backordered = fields.Monetary(string="Total", compute="_compute_backorder", store=True)

    stage = fields.Selection([
        ('undefined', 'Undefined'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ], string='Status', default='undefined', compute='_compute_sale_line_stage', store=True)

    @api.depends('order_id.stage_id')
    def _compute_sale_line_stage(self):
        for line in self:
            if line.order_id.stage_id:
                switcher = {
                    self.env.ref('phd_sale.phd_sale_order_stage_sale_order').id: True,
                    self.env.ref('phd_sale.phd_sale_order_stage_on_hold').id: True,
                    self.env.ref('phd_sale.phd_sale_order_stage_partially_shipped').id: True,
                    self.env.ref('phd_sale.phd_sale_order_stage_fully_shipped').id: True,
                }
                if switcher.get(line.order_id.stage_id.id, False):
                    line.stage = 'open'
                elif line.order_id.stage_id.id == self.env.ref('phd_sale.phd_sale_order_stage_closed').id:
                    line.stage = 'closed'
                else:
                    line.stage = 'undefined'

    @api.constrains('qty_delivered', 'move_ids')
    def _check_qty_delivered(self):
        if self.order_id.stage_id in [self.env.ref('phd_sale.phd_sale_order_stage_sale_order'),
                                      self.env.ref('phd_sale.phd_sale_order_stage_partially_shipped')]:
            is_partially_shipped = False
            for line in self:
                if not float_is_zero(line.qty_delivered, precision_digits=0):
                    if float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=0) == -1:
                        move = line.move_ids.filtered(lambda x: x.state not in ['draft','cancel','done'])
                        if move:
                            self.order_id.write({'stage_id': self.env.ref('phd_sale.phd_sale_order_stage_partially_shipped').id})
                            is_partially_shipped = True
            lines = self.filtered(lambda x: not float_is_zero(x.qty_delivered, precision_digits=0))
            if not is_partially_shipped and lines:
                self.order_id.write({'stage_id': self.env.ref('phd_sale.phd_sale_order_stage_fully_shipped').id})

    @api.depends('qty_delivered','qty_to_invoice')
    def _compute_unbilled_sales(self):
        for record in self:
            if float_compare(record.qty_delivered, record.qty_to_invoice,precision_digits=0) == 0:
                record.is_unbilled_sales = True
            else:
                record.is_unbilled_sales = False

    def _compute_trigger_field(self):
        for record in self:
           record.trigger_field = 1
           record.expected_delivery_date =  record.order_id.expected_date

    @api.depends('move_ids', 'move_ids.state', 'move_ids.date_expected')
    def _compute_backorder(self):
        for line in self:
            move_ids = line.move_ids.filtered(lambda x: x.state not in ('done','cancel') and x.backorder_id)
            if move_ids:
                line.qty_backordered = sum(move.product_uom_qty for move in move_ids)
                line.total_qty_backordered = line.qty_backordered * line.price_unit
                delay_tracker = line.order_id.delay_tracker_ids
                original_date = False
                if delay_tracker:
                    dates = []
                    for date in delay_tracker:
                        if isinstance(date.promised_date, dt):
                            dates.append(date.promised_date)
                    original_date = min(dates)
                if original_date:
                    date_expected = fields.Date.from_string(move_ids.sorted(key=lambda e: e.date_expected)[-1].date_expected)
                    original_date = fields.Date.from_string(original_date)
                    line.days_late = (date_expected - original_date).days
                # for move in move_ids:

            else:
                line.qty_backordered = 0
                line.total_qty_backordered = 0
                line.days_late = 0