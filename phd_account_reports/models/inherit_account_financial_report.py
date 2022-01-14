# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast

from odoo import models, fields, api, _
from odoo.addons.web.controllers.main import clean_action
from odoo.osv import expression


class ReportAccountFinancialReport(models.Model):
    _inherit = 'account.financial.html.report'

    analytic_report = fields.Boolean(string="Analytic Report")

    @api.model
    def _get_analytic_options_date_domain(self, options):
        def create_date_domain(options_date):
            date_field = options_date.get('date_field', 'date')
            # Get end date domain
            domain = [(date_field, '<=', options_date['date_to'])]
            if options_date['mode'] == 'range':
                # Get start date domain
                strict_range = options_date.get('strict_range')
                if not strict_range:
                    domain += [
                        '|',
                        (date_field, '>=', options_date['date_from']),
                        ('general_account_id.user_type_id.include_initial_balance', '=', True)
                    ]
                else:
                    domain += [(date_field, '>=', options_date['date_from'])]
            return domain

        if not options.get('date'):
            return []
        return create_date_domain(options['date'])

    def open_journal_items(self, options, params):
        # If the report based on analytic line and analytic account filter is used, open the Analytic Line list view
        # else get the view of Account move line from Odoo
        if self.analytic_report and options.get('analytic_accounts'):
            action = self.env.ref('analytic.account_analytic_line_action').read()[0]
            action = clean_action(action)
            domain = []
            ctx = self._context.copy()
            # Get the financial account domain
            if params and 'id' in params:
                active_id = self._get_caret_option_target_id(params['id'])
                domain = expression.AND([domain, [('general_account_id', '=', active_id)]])
            # Get analytic account based on the filter
            if options.get('analytic_accounts'):
                analytic_accounts = [int(r) for r in options['analytic_accounts']]
                domain = expression.AND([domain, [('account_id', 'in', analytic_accounts)]])
            # Get analytic tag based on the filter
            if options.get('analytic_tags'):
                analytic_tags = [int(r) for r in options['analytic_tags']]
                domain = expression.AND([domain, [('tag_ids', 'in', analytic_tags)]])
            # Get date domain
            if options.get('date'):
                domain = expression.AND([domain, self._get_analytic_options_date_domain(options)])
            action['name'] = _('Analytic Items')
            action['domain'] = domain
            action['context'] = ctx
        else:
            action = super(ReportAccountFinancialReport, self).open_journal_items(options, params)
        return action


class AccountFinancialReportLine(models.Model):
    _inherit = 'account.financial.html.report.line'

    def _query_get_select_sum(self, currency_table):
        """ Little function to help building the SELECT statement when computing the report lines.

            @param currency_table: dictionary containing the foreign currencies (key) and their factor (value)
                compared to the current user's company currency
            @returns: the string and parameters to use for the SELECT
        """
        context = self._context
        if context.get('analytic_report') and context.get('analytic_account_ids'):
            decimal_places = self.env.company.currency_id.decimal_places
            extra_params = []
            # Copy from _query_get_select_sum function of account_reports.account.financial.html.report.line model
            # but get the analytic line amount instead of account move line balance
            select = '''
                COALESCE(SUM(-\"account_move_line__analytic_line\".amount), 0) AS balance,
                COALESCE(SUM(\"account_move_line\".amount_residual), 0) AS amount_residual,
                COALESCE(SUM(\"account_move_line\".debit), 0) AS debit,
                COALESCE(SUM(\"account_move_line\".credit), 0) AS credit
            '''
            if currency_table:
                select = 'COALESCE(SUM(CASE '
                for currency_id, rate in currency_table.items():
                    extra_params += [currency_id, rate, decimal_places]
                    select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".balance * %s, %s) '
                select += 'ELSE \"account_move_line\".balance END), 0) AS balance, COALESCE(SUM(CASE '
                for currency_id, rate in currency_table.items():
                    extra_params += [currency_id, rate, decimal_places]
                    select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".amount_residual * %s, %s) '
                select += 'ELSE \"account_move_line\".amount_residual END), 0) AS amount_residual, COALESCE(SUM(CASE '
                for currency_id, rate in currency_table.items():
                    extra_params += [currency_id, rate, decimal_places]
                    select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".debit * %s, %s) '
                select += 'ELSE \"account_move_line\".debit END), 0) AS debit, COALESCE(SUM(CASE '
                for currency_id, rate in currency_table.items():
                    extra_params += [currency_id, rate, decimal_places]
                    select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".credit * %s, %s) '
                select += 'ELSE \"account_move_line\".credit END), 0) AS credit'

            res = select, extra_params
        else:
            res = super(AccountFinancialReportLine, self)._query_get_select_sum(currency_table)

        return res

    def _get_lines(self, financial_report, currency_table, options, linesDicts):
        analytic_report = financial_report.analytic_report

        res = super(AccountFinancialReportLine, self.with_context(analytic_report=analytic_report))._get_lines(
            financial_report, currency_table, options, linesDicts)

        return res
