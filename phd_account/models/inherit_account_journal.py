# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('is_credit_card_charge', False):
            journal_ids = self.env['account.journal'].search([('is_credit_card', '=', True)]).ids
            args = [['id', 'in', journal_ids]]
        return self._name_search(name, args, operator, limit=limit)
