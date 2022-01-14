from odoo import api, fields, models, _


class SettlementReport(models.Model):
    _name = 'settlement.report'
    _description = 'Settlement Report'

    name = fields.Char(string='Settlement ID')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain="[('type', '=', 'bank')]")
    date = fields.Date(string='Date')
    amount = fields.Float(string='Amount')
    is_reconciled = fields.Boolean(string='Reconciled')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], string='State', default='draft')
    batch_report_ids = fields.One2many('payarc.batch.report', 'settlement_id', string='Batch Reports')

    def confirm(self):
        self.update({
            'state': 'confirm'
        })

