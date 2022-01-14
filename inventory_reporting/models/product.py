# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def name_get(self):
        res = []
        if self.env.context.get('default_code'):
            for product in self:
                name = product.default_code
                res.append((product.id, name))
            return res
        return super(ProductProduct, self).name_get()
