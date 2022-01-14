# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

import re
import logging

from odoo import api, models
from odoo.addons.account.models.reconciliation_widget import AccountReconciliation

_logger = logging.getLogger(__name__)

class AccountReconciliation(AccountReconciliation):
    """Manage 'account.reconciliation.widget' model. Overriding model."""
#     _inherit = "account.reconciliation.widget"

    @api.model
    def get_move_lines_for_bank_statement_line(self, st_line_id, partner_id=None, excluded_ids=None, search_str=False, offset=0, limit=None):
        """ Returns move lines for the bank statement reconciliation widget,
            formatted as a list of dicts
            :param st_line_id: ids of the statement lines
            :param partner_id: optional partner id to select only the moves
                line corresponding to the partner
            :param excluded_ids: optional move lines ids excluded from the
                result
            :param search_str: optional search (can be the amout, display_name,
                partner name, move line name)
            :param offset: offset of the search result (to display pager)
            :param limit: number of the result to search
        """
        st_line = self.env['account.bank.statement.line'].browse(st_line_id)

        # Blue lines = payment on bank account not assigned to a statement yet
        aml_accounts = [
            st_line.journal_id.default_credit_account_id.id,
            st_line.journal_id.default_debit_account_id.id
        ]

        if partner_id is None:
            partner_id = st_line.partner_id.id

        domain = self._domain_move_lines_for_reconciliation(st_line, aml_accounts, partner_id, excluded_ids=excluded_ids, search_str=search_str)
        domain.append(("account_id", "in", aml_accounts))
        _logger.info("domain" + str(domain))
        recs_count = self.env['account.move.line'].search_count(domain)
        aml_recs = self.env['account.move.line'].search(domain, offset=offset, limit=limit, order="date_maturity desc, id desc")
        target_currency = st_line.currency_id or st_line.journal_id.currency_id or st_line.journal_id.company_id.currency_id
        return self._prepare_move_lines(aml_recs, target_currency=target_currency, target_date=st_line.date, recs_count=recs_count)

    
    
#     @api.model
#     def _domain_move_lines(self, search_str):
#         a = 6 /0
#         """Returns the domain from the search_str search. Overriding method."""
#         # CALL SUPER
#         str_domain = super(AccountReconciliationWidget, self)._domain_move_lines(search_str=search_str)

# #         ids = []
# #         domain = [("full_reconcile_id", "=", False), ("balance", "!=", 0), ("account_id.reconcile", "=", True), ("x_channel_name", "ilike", search_str)]
        
# #         for account_move_line_id in self.env['account.move.line'].search(domain):
# #             ids.append(account_move_line_id.id)

        
#         str_domain = [("account_id.id", "=", 260)] + str_domain
#         _logger.info("domain" + str(str_domain))
# #
        
#         return str_domain
