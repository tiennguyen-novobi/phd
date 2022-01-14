# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    z_score = fields.Float(string='Z-score', default=lambda self: self.env.company.default_assigning_z_score,
                           required=True)
    eligible_primary_vendor_ids = fields.Many2many('res.partner', string='Eligible Vendors',
                                                   compute='_compute_eligible_vendors', store=False)
    primary_vendor_id = fields.Many2one('res.partner', string='Primary Vendor', compute='_compute_primary_vendor',
                                        inverse='_set_primary_vendor', store=True)
    purchase_lead_time = fields.Integer(string='Purchase Lead Time', compute='_compute_purchase_info', store=True)
    minimum_purchase_qty = fields.Float(string='Minimum Order Quantity', compute='_compute_purchase_info', store=True)
    safety_stock_method = fields.Selection(
        string='Safety Stock Calculation',
        selection=[('automatic', 'Automatic'), ('manual', 'Manual')], default='automatic',
        help='Safety Stock will be calculated automatically using normal distribution with uncertainty about the demand',
        required=True)
    safety_stock = fields.Float(digits='Product Unit of Measure', required=True)

    def get_vendor_pricelist(self):
        if self.product_tmpl_id._origin.product_variant_count < 2:
            sellers = self.seller_ids
        else:
            sellers = self.variant_seller_ids
        return sellers

    @api.depends('seller_ids', 'variant_seller_ids')
    def _compute_eligible_vendors(self):
        for product in self:
            sellers = product.get_vendor_pricelist()
            product.eligible_primary_vendor_ids = sellers.name

    @api.depends('seller_ids', 'variant_seller_ids',
                 'product_tmpl_id.seller_ids.name', 'product_tmpl_id.variant_seller_ids.name')
    def _compute_primary_vendor(self):
        for product in self:
            sellers = product.get_vendor_pricelist()
            if not product.primary_vendor_id or product.primary_vendor_id not in sellers.name._origin:
                product.primary_vendor_id = sellers and sellers[0].name or False

    def _set_primary_vendor(self):
        pass

    @api.depends('primary_vendor_id')
    def _compute_purchase_info(self):
        for product in self:
            if product.primary_vendor_id:
                sellers = product.get_vendor_pricelist()
                pricelist = sellers.filtered(lambda s: s.name.id == product.primary_vendor_id.id)
                matched_pricelist = len(pricelist) > 1 and pricelist[0] or pricelist
                product.purchase_lead_time = matched_pricelist.delay if matched_pricelist else self.env.company.default_purchase_lead_time
                product.minimum_purchase_qty = matched_pricelist.min_qty if matched_pricelist else 0
            else:
                product.purchase_lead_time = self.env.company.default_purchase_lead_time
                product.minimum_purchase_qty = 0

    @api.constrains('z_score')
    def _check_z_score_validity(self):
        for product in self:
            if float_compare(product.z_score, 0, precision_digits=2) <= 0:
                raise UserError(_("Assigning Z-score should be greater than 0"))

    def write(self, vals):
        if 'seller_ids' in vals or 'variant_seller_ids' in vals:
            if self.product_tmpl_id.product_variant_count < 2:
                seller_value = vals.get('variant_seller_ids', []) + vals.get('seller_ids', [])
                vals['seller_ids'] = seller_value
                vals.pop('variant_seller_ids', {})
            else:
                seller_value = vals.get('seller_ids', []) + vals.get('variant_seller_ids', [])
                vals['variant_seller_ids'] = seller_value
                vals.pop('seller_ids', {})
        res = super(ProductProduct, self).write(vals)
        if 'forecasted_demand_ok' in vals:
            self.insert_product_into_stock_status_tracking(vals['forecasted_demand_ok'])
        return res

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        if 'forecasted_demand_ok' in vals:
            res.insert_product_into_stock_status_tracking(vals['forecasted_demand_ok'])
        return res

    def insert_product_into_stock_status_tracking(self, is_forecasted_demand=False):
        if is_forecasted_demand:
            existing_records = self.env['stock.status.report.line'].search_read([('product_id', 'in', self.ids)],
                                                                                ['product_id'])
            existing_product_ids = list(map(lambda x: x['product_id'][0], existing_records))
            values = list(map(lambda x: {"product_id": x}, set(self.ids) - set(existing_product_ids)))
            self.env['stock.status.report.line'].create(values)

    @api.model
    def compute_safety_stock(self):
        order_date_interval = self.env.company.default_order_analysis_interval or 6
        end_date = fields.Date.today()
        start_date = end_date - relativedelta(months=order_date_interval)
        query_stmt = """
            SELECT product_id, z_score, purchase_lead_time, 
                    stddev_pop(sale_qty) as demand_stddev, 
                    z_score*sqrt(purchase_lead_time*stddev_pop(sale_qty)) as safety_stock
            FROM (
                SELECT ts.date_order, product.product_id, product.z_score, product.purchase_lead_time,
                    COALESCE(sale_qty, 0) as sale_qty
                FROM (
                    SELECT ts::date as date_order
                    FROM generate_series('{start_date}', '{end_date}', '1 day'::interval) ts
                ) ts NATURAL JOIN (
                    SELECT distinct pp.id as product_id, z_score, purchase_lead_time
                    FROM product_product pp
                    WHERE forecasted_demand_ok IS True 
                        AND safety_stock_method = 'automatic'
                ) product LEFT JOIN
                    (
                        SELECT date_order, product_id, 
                        SUM((CASE WHEN suom.factor = 0 OR suom.factor IS NULL
                                   THEN demand.sale_qty
                                   ELSE (demand.sale_qty * COALESCE(puom.factor, 1) / suom.factor) END)) as sale_qty
                        FROM (
                            SELECT *
                            FROM actual_daily_sales_demand
                            WHERE date_order <= '{end_date}' AND date_order >= '{start_date}'
                        ) demand
                            JOIN product_product pp ON demand.product_id = pp.id
                            JOIN product_template pt ON pp.product_tmpl_id = pt.id
                            JOIN uom_uom puom ON pt.uom_id = puom.id
                            JOIN uom_uom suom ON demand.sale_uom_id = suom.id
                        GROUP BY date_order, product_id
                    ) demand ON ts.date_order = demand.date_order AND product.product_id = demand.product_id
            ) result
            GROUP BY product_id, z_score, purchase_lead_time
        """.format(start_date=start_date, end_date=end_date)
        self.env.cr.execute(query_stmt)
        result = self.env.cr.dictfetchall()
        for record in result:
            safety_stock = record.get('safety_stock', 0)
            demand_stddev = record.get('demand_stddev', 0)
            product = self.env['product.product'].browse(record['product_id'])
            product.update({'safety_stock': safety_stock})
            _logger.log(25, "UPDATE SAFETY STOCK={} with stddev={} for '{}' product_id = {}".format(safety_stock,
                                                                                                    demand_stddev,
                                                                                                    product.name,
                                                                                                    product.id))
