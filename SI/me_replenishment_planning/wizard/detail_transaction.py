# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class DetailTransaction(models.TransientModel):
    _name = "detail.transaction"
    _description = "Open detail transactions of shortage report"

    production_id = fields.Many2one(comodel_name='mrp.production', string='Manufacturing Order')
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order')
    status = fields.Char('Status', compute='_compute_status', store=True)
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'))
    date_to_complete = fields.Datetime('Date to be completed')

    @api.depends('production_id', 'purchase_order_id')
    def _compute_status(self):
        production_env = self.env['mrp.production']
        purchase_env = self.env['purchase.order']
        for rec in self:
            status = ''
            production_id = rec.production_id
            purchase_order_id = rec.purchase_order_id
            if production_id:
                status = production_id.state and dict(production_env._fields['state'].selection).get(production_id.state) or ''
            if purchase_order_id:
                status = purchase_order_id.state and dict(purchase_env._fields['state'].selection).get(
                    purchase_order_id.state) or ''
            rec.status = status

