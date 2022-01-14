from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_integrate_with_payarc = fields.Boolean(string='Integrate with PayArc / Authorize.Net')
    payarc_access_token = fields.Char(string='PayArc Access Token')
    authorize_login_id = fields.Char(string='Authorize Login ID')
    authorize_transaction_key = fields.Char(string='Authorize Transaction Key')
    payarc_sales_account_id = fields.Many2one('account.account', string='Sales Account', domain="[('deprecated', '=', False)]")
    payarc_fees_account_id = fields.Many2one('account.account', string='Fees Account', domain="[('deprecated', '=', False)]")
    payarc_reserve_account_id = fields.Many2one('account.account', string='Reserve Account', domain="[('deprecated', '=', False)]")
    payarc_transit_account_id = fields.Many2one('account.account', string='Transit Account', domain="[('deprecated', '=', False)]")

    def action_open_batch_report(self):
        action = self.env.ref('phd_payarc.phd_batch_report_action').read()[0]
        action['domain'] = [('journal_id', '=', self.id)]
        return action

    def action_open_settlement_report(self):
        action = self.env.ref('phd_payarc.phd_settlement_report_action').read()[0]
        action['domain'] = [('journal_id', '=', self.id)]
        action['context'] = {'default_journal_id': self.id}
        return action
