# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    ###################################
    # FIELDS
    ###################################

    buyer_ids = fields.One2many('product.customerinfo', 'product_id', 'Customer')

    @api.constrains('buyer_ids')
    def _check_unique_customer_info(self):
        for record in self:
            partner_ids = list(map(lambda buyer: buyer.partner_id, record.buyer_ids))
            if len(partner_ids) > len(set(partner_ids)):
                raise ValidationError(_('Vendor already exists on this product'))
