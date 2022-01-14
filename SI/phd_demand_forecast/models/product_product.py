# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    forecasted_demand_ok = fields.Boolean(string='Can be Forecasted', default=False)
    
    def action_include_product_forecasting(self):
        self.forecasted_demand_ok = True
    
    def action_exclude_product_forecasting(self):
        self.forecasted_demand_ok = False
    
    def action_product_forecasted_demand_report(self):
        self.ensure_one()
        action = self.env.ref('phd_demand_forecast.stock_forcasted_demand_product_product_action').read()[0]
        action['context'] = {'default_product_id': self.id}
        return action
