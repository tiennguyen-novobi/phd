# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ###################################
    # FIELDS
    ###################################
    is_product_label = fields.Boolean(string='Product Label')
    is_creatine = fields.Boolean(string='Creatine')
    is_royalty = fields.Boolean(string='Royalty')

    @api.model
    def get_createtine_cost(self):
        creatine = self.env['product.product'].search([('is_creatine','=', True)], limit=1)
        if creatine:
            return creatine.standard_price
        else:
            return 0

