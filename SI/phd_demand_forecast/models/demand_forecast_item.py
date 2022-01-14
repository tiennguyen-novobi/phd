# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DemandForecastItem(models.Model):
    _name = 'demand.forecast.item'
    _description = "Demand Forecast Item"
    _rec_name = 'product_id'
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_default_code = fields.Char(string='SKU', related='product_id.default_code')
    product_uom_id = fields.Many2one(string='Unit of Measure', related='product_id.uom_id')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    week_end_date = fields.Date(string='End Date of Week', required=True)
    demand_qty = fields.Float(string='Forecasted Demand', default=0, digits='Product Unit of Measure', required=True)
    
    _sql_constraints = [
        ('unique_demand', 'unique (product_id, week_end_date, partner_id)',
         'The forecasted demand in a specific week of a product for a customer must be unique!')
    ]
    
    @api.constrains('week_end_date')
    def _check_end_date_of_week(self):
        for item in self:
            week_end_day = (int(self.env['res.lang']._lang_get(self.env.user.lang).week_start) - 2) % 7
            if item.week_end_date.weekday() != week_end_day:
                raise ValidationError(_("The end date of week is invalid."))
