from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    paypal_journal_id = fields.Many2one('account.journal', string='Journal', domain="[('type', '=', 'bank')]")
    paypal_merchant = fields.Char(string='Merchant')
    paypal_sales_account_id = fields.Many2one('account.account', string='Sales Account',
                                              domain="[('deprecated', '=', False)]")
    paypal_fee_account_id = fields.Many2one('account.account', string='Fee Account',
                                            domain="[('deprecated', '=', False)]")
    paypal_bank_account_id = fields.Many2one('account.account', string='Bank Account',
                                             domain="[('deprecated', '=', False)]")
    paypal_analytic_account_id = fields.Many2one('account.account', string='Analytic Account',
                                                 domain="[('deprecated', '=', False)]")
    paypal_analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
