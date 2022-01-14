# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo.exceptions import ValidationError, UserError

class PHDProduct(models.Model):
    _name = "phd.mko.line"
    _order = 'sequence'

    mko_id = fields.Many2one('phd.mko', string='Order Reference', required=True, ondelete='cascade', index=True,
                               copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    funding = fields.Monetary(string='Funding')
    quantity = fields.Integer('Quantity', copy=False, digits='Quantity')
    product_id = fields.Many2one('product.product', string='Product', change_default=True, ondelete='restrict', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount', store=True, compute="_compute_amount")
    stage_id = fields.Many2one(related='mko_id.stage_id')
    partner_id = fields.Many2one(related='mko_id.partner_id')
    date_order = fields.Date(related='mko_id.date_order')
    promotion_period_from = fields.Date(related='mko_id.promotion_period_from', string="Promotion From")
    promotion_period_to = fields.Date(related='mko_id.promotion_period_to', string="Promotion To")
    sku = fields.Char(string="Product (SKU)", related='product_id.default_code')

    @api.depends('quantity', 'funding')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.funding

    @api.constrains('funding')
    def _check_funding(self):
        for line in self:
            if line.funding <= 0:
                raise ValidationError(_('Funding must be greater than 0.'))