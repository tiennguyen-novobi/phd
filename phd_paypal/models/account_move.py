from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    paypal_transaction_id = fields.Many2one('paypal.transaction', string='Paypal Transaction', copy=False, ondelete='set null')

    # Copy fields created by Odoo Studio
    x_studio_dtc_order_id = fields.Char()
    x_studio_transaction_id = fields.Char()
    x_studio_merchant = fields.Char()
    x_studio_authorization_id = fields.Char()
