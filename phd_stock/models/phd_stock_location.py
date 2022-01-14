# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    stock_location_alias = fields.Char(string='Alias')
    is_visible = fields.Boolean(string='Is Visible')

    def name_get(self):
        if self.env.context.get('forecasted_qty', False):
            res = []
            for record in self:
                res.append((record['id'],
                            record.stock_location_alias if record.stock_location_alias else record.complete_name))
            return res
        else:
            return super(StockLocation, self).name_get()