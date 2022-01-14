from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    braintree_merchant_id = fields.Char(string='Braintree Merchant ID', config_parameter='braintree_merchant_id')
    braintree_public_key = fields.Char(string='Braintree Public Key', config_parameter='braintree_public_key')
    braintree_private_key = fields.Char(string='Braintree Private Key', config_parameter='braintree_private_key')

    paypal_journal_id = fields.Many2one('account.journal', related='company_id.paypal_journal_id', readonly=False, domain="[('type', '=', 'bank')]")
    paypal_merchant = fields.Char(related='company_id.paypal_merchant', readonly=False, domain="[('deprecated', '=', False)]")
    paypal_sales_account_id = fields.Many2one('account.account', related='company_id.paypal_sales_account_id', readonly=False, domain="[('deprecated', '=', False)]")
    paypal_fee_account_id = fields.Many2one('account.account', related='company_id.paypal_fee_account_id', readonly=False, domain="[('deprecated', '=', False)]")
    paypal_bank_account_id = fields.Many2one('account.account', related='company_id.paypal_bank_account_id', readonly=False, domain="[('deprecated', '=', False)]")
    paypal_analytic_account_id = fields.Many2one('account.account', related='company_id.paypal_analytic_account_id', readonly=False, domain="[('deprecated', '=', False)]")
    paypal_analytic_tag_ids = fields.Many2many('account.analytic.tag', related='company_id.paypal_analytic_tag_ids', readonly=False)
