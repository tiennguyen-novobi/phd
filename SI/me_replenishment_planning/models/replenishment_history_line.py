# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ReplenishmentTrackerLine(models.Model):
    _name = "replenishment.history.line"
    _description = "Replenishment History Line"

    ###############################
    # FIELDS DECLARATION
    ###############################
    replenishment_id = fields.Many2one(
        'replenishment.history', string='Replenishment Reference', required=True,
        ondelete='cascade', index=True, readonly=True)
    order_type = fields.Selection([
        ('by_purchase', _('By Purchase')),
        ('by_manufacture', _('By Manufacture'))
    ], string='Order Type', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    default_code = fields.Char(string='Internal Reference', related='product_id.default_code', readonly=True)
    order_quantity = fields.Float(string='Order Quantity', readonly=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_id.product_tmpl_id.uom_id', readonly=True,
        help="This comes from the product form.")
    purchase_uom = fields.Many2one(
        'uom.uom', 'Purchase Unit of Measure',
        related='product_id.product_tmpl_id.uom_po_id', readonly=True,
        help="This comes from the product form.")
    bom_uom = fields.Many2one(
        'uom.uom', 'Manufacture Unit of Measure', readonly=True, help="This comes from the manufacturing order.")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.user.company_id.id, readonly=True)
