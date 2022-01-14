# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductCustomerInfo(models.Model):
    _name = "product.customerinfo"

    ###################################
    # FIELDS
    ###################################
    partner_id = fields.Many2one(
        'res.partner', 'Customer',
        ondelete='cascade', required=True,
        help="Customer of this product")
    product_name = fields.Char('Customer Product Name', required=True)

    product_id = fields.Many2one('product.product', 'Product Variant', ondelete='cascade')
