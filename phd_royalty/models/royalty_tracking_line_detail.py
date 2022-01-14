# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import tools


class RoyaltyTrackingLineDetail(models.Model):
    _name = "royalty.tracking.line.detail"
    _description = 'Royalty Tracking Line Detail'
    _order = 'manufacture_date asc'

    ###################################
    # FIELDS
    ###################################

    royalty_tracking_line_id = fields.Many2one('royalty.tracking.line')

    manufacture_date = fields.Datetime(string='Manufacture Date', readonly=True)
    production_id = fields.Many2one('mrp.production', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', readonly=True)
    purchase_id = fields.Many2one('purchase.order', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    finished_product_id = fields.Many2one('product.product', readonly=True)
    product_uom_qty = fields.Float(digits='Product Unit of Measure', readonly=True)
