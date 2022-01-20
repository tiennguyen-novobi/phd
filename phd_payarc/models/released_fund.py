from odoo import models, fields, api


class ReleasedFund(models.Model):
    _name = 'released.fund'
    _description = 'Released Fund'

    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain="[('type', '=', 'bank')]")
