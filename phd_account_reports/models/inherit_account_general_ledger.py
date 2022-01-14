# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

REF_COLUMN_IDX = 1


class AccountGeneralLedgerReport(models.AbstractModel):
    _inherit = 'account.general.ledger'

    @api.model
    def _get_aml_line(self, options, account, aml, cumulated_balance):
        res = super(AccountGeneralLedgerReport, self)._get_aml_line(options, account, aml, cumulated_balance)

        if res.get('columns') and len(res.get('columns')) > REF_COLUMN_IDX + 1:
            res['columns'][REF_COLUMN_IDX].update({'class': 'whitespace_print o_account_report_line_ellipsis'})

        return res
