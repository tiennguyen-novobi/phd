# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PHDPaymentDeposit(models.Model):
    _name = 'phd.payment.deposit'

    description = fields.Text(string="Description", help="Description")
    account_id = fields.Many2one('account.account', string='Account')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Monetary(string='Price')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal_price', store=True)
    payment_id = fields.Many2one('account.payment')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id')
    account_line_id = fields.Many2one('account.move.line')

    @api.depends('price_unit', 'quantity')
    def _compute_subtotal_price(self):
        for record in self:
            record.price_subtotal = record.quantity * record.price_unit
