# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging
import lxml.html
from odoo.tools.misc import xlsxwriter
from odoo import models, fields, api, _, _lt
from odoo.tools.misc import format_date
from odoo.tools import config
from datetime import datetime
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)

REF_COLUMN_IDX = 1


class AccountGeneralLedgerReport(models.AbstractModel):
    _name = 'phd.account.general.ledger'
    _inherit = 'account.general.ledger'

    filter_account_type = True

    def _is_negative(self, amount):
        is_negative = False
        if self.env.company.currency_id.compare_amounts(amount, 0) < 0 and self._context.get('print_mode', False) and not self._context.get('is_print_pdf', False):
            is_negative = True
        return is_negative

    def _get_templates(self):
        templates = super(AccountGeneralLedgerReport, self)._get_templates()
        templates['search_template'] = 'phd_account_reports.general_ledger_search_template'
        templates['line_template'] = 'phd_account_reports.general_leager_expanded_line_template'
        templates['main_template'] = 'phd_account_reports.general_ledger_expanded_main_template'
        return templates

    @api.model
    def _get_super_columns(self, options):
        date_from = datetime.strptime(options.get('date')['date_from'], DEFAULT_SERVER_DATE_FORMAT).strftime("%m/%d/%Y")
        date_to = datetime.strptime(options.get('date')['date_to'], DEFAULT_SERVER_DATE_FORMAT).strftime("%m/%d/%Y")
        header = '&"Arial,Bold"&12%s' % self.env.user.company_id.name + '\n' + \
                 '&"Arial,Bold"&14%s' % self._get_report_name() + '\n' + \
                 '&"Arial,Bold"&12 %s &"Arial,Bold"&12- &"Arial,Bold"&12 %s' % (date_from, date_to) + '\n'
        return {'header': header}

    @api.model
    def _get_columns_name(self, options):
        columns = [
            {'name': '' if not self._context.get('print_mode', False) else 'GL Account'},
            {'name': _('Date'), 'class': 'date'},
            {'name': _('Reference')},
            {'name': _('Memo/Label')},
            {'name': _('Communication')},
            {'name': _('Analytic Account')},
            {'name': _('Analytic Tag(s)')},
            {'name': _('Partner')},
            {'name': _('Journal')},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'}
        ]
        if self._context.get('print_mode', False):
            if self._context.get('is_print_pdf', False):
                columns = [
                    {'name': '' if not self._context.get('print_mode', False) else 'GL Account'},
                    {'name': _('Date'), 'class': 'date'},
                    {'name': _('Reference')},
                    {'name': _('Memo/Label')},
                    {'name': _('Partner')},
                    {'name': _('Debit'), 'class': 'number'},
                    {'name': _('Credit'), 'class': 'number'},
                    {'name': _('Balance'), 'class': 'number'}
                ]
            columns.insert(2, {'name': 'Document ID'})
        return columns

    @api.model
    def _get_general_ledger_lines(self, options, line_id=None):
        lines = []
        aml_lines = []
        options_list = self._get_options_periods_list(options)
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        date_from = fields.Date.from_string(options['date']['date_from'])
        company_currency = self.env.company.currency_id

        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options_list, expanded_account=expanded_account)

        total_debit = total_credit = total_balance = 0.0
        for account, periods_results in accounts_results:
            # No comparison allowed in the General Ledger. Then, take only the first period.
            results = periods_results[0]

            is_unfolded = 'account_%s' % account.id in options['unfolded_lines']

            # account.account record line.
            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})

            # Check if there is sub-lines for the current period.
            max_date = account_sum.get('max_date')
            has_lines = max_date and max_date >= date_from or False

            amount_currency = account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0)
            debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
            balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

            if not self._context.get('print_mode') or len(results.get('lines', [])) == 0:
                lines.append(
                    self._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines))

            total_debit += debit
            total_credit += credit
            total_balance += balance

            if has_lines and (unfold_all or is_unfolded):
                # Initial balance line.
                account_init_bal = results.get('initial_balance', {})

                cumulated_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                lines.append(self._get_initial_balance_line(
                    options, account,
                    account_init_bal.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    account_init_bal.get('debit', 0.0) + account_un_earn.get('debit', 0.0),
                    account_init_bal.get('credit', 0.0) + account_un_earn.get('credit', 0.0),
                    cumulated_balance,
                ))

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES

                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_balance += aml['balance']
                    lines.append(self._get_aml_line(options, account, aml, company_currency.round(cumulated_balance)))

                    load_more_remaining -= 1
                    load_more_counter -= 1
                    aml_lines.append(aml['id'])

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_load_more_line(
                        options, account,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))

                # Account total line.
                lines.append(self._get_account_total_line(
                    options, account,
                    account_sum.get('amount_currency', 0.0),
                    account_sum.get('debit', 0.0),
                    account_sum.get('credit', 0.0),
                    account_sum.get('balance', 0.0),
                ))

        if not line_id:
            # Report total line.
            lines.append(self._get_total_line(
                options,
                total_debit,
                total_credit,
                company_currency.round(total_balance),
            ))

            # Tax Declaration lines.
            journal_options = self._get_options_journals(options)
            if len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
                lines += self._get_tax_declaration_lines(
                    options, journal_options[0]['type'], taxes_results
                )
        if self.env.context.get('aml_only'):
            return aml_lines
        return lines

    @api.model
    def _get_aml_line(self, options, account, aml, cumulated_balance):
        if aml['payment_id']:
            caret_type = 'account.payment'
        elif aml['move_type'] in ('in_refund', 'in_invoice', 'in_receipt'):
            caret_type = 'account.invoice.in'
        elif aml['move_type'] in ('out_refund', 'out_invoice', 'out_receipt'):
            caret_type = 'account.invoice.out'
        else:
            caret_type = 'account.move'

        ref_name = False
        if aml.get('ref', False) and len(aml['ref']) > 15:
            ref_name = aml['ref'][:15] + "..."

        line_name = False
        if aml.get('name', False) and len(aml['name']) > 20:
            line_name = aml['name'][:20] + "..."

        vals = {
            'id': aml['id'],
            'caret_options': caret_type,
            'class': 'whitespace_print',
            'parent_id': 'account_%d' % aml['account_id'],
            'name': aml['move_name'] if not self._context.get('print_mode', False) else '%s %s' % (
                account.code, account.name),
            'columns': [
                {'name': format_date(self.env, aml['date']), 'class': 'date'},
                {'name': ref_name if self._context.get('print_mode', False) and self._context.get('is_print_pdf', False) and ref_name else aml['ref'], 'class': 'whitespace_print'},
                {'name': line_name if self._context.get('print_mode', False) and self._context.get('is_print_pdf', False) and line_name else aml['name'], 'class': 'whitespace_print'},
                {'name': self.with_context(no_format=self._context.get('print_mode', False))._format_aml_name(aml['name'], aml['ref'], aml['move_name']), 'class': 'whitespace_print'},
                {'name': aml['analytic_account_name'], 'class': 'whitespace_print'},
                {'name': aml['analytic_tags_name'], 'class': 'whitespace_print'},
                {'name': aml['partner_name'], 'title': aml['partner_name'], 'class': 'whitespace_print'},
                {'name': aml['journal_code'], 'title': aml['journal_code'], 'class': 'whitespace_print'},
                {'name':  '(%s)' % self.format_value(aml['debit'], blank_if_zero=True) if self._is_negative(aml['debit']) else self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number', 'is_negative': self._is_negative(aml['debit'])},
                {'name': '(%s)' % self.format_value(aml['credit'], blank_if_zero=True) if self._is_negative(aml['credit']) else self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number', 'is_negative': self._is_negative(aml['credit'])},
                {'name': '(%s)' % self.format_value(cumulated_balance) if self._is_negative(cumulated_balance) else self.format_value(cumulated_balance), 'class': 'number', 'is_negative': self._is_negative(cumulated_balance)},
            ],
            'level': 2
        }
        if self._context.get('print_mode', False):
            vals['columns'].insert(1, {'name': aml['move_name']})
            if self._context.get('is_print_pdf', False):
                vals['columns'].pop(4)
                vals['columns'].pop(4)
                vals['columns'].pop(4)
                vals['columns'].pop(5)
        return vals

    @api.model
    def _get_account_total_line(self, options, account, amount_currency, debit, credit, balance):
        vals = {
            'id': 'total_%s' % account.id,
            'class': 'o_account_reports_domain_total',
            'parent_id': 'account_%s' % account.id,
            'name': _('Total') if not self._context.get('is_print_pdf', False) else '%s %s' % (
                account.code, account.name),
            'columns': [
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': '(%s)' % self.format_value(debit) if self._is_negative(debit) else self.format_value(debit), 'class': 'number', 'is_negative': self._is_negative(debit)},
                {'name': '(%s)' % self.format_value(credit) if self._is_negative(credit) else self.format_value(credit), 'class': 'number', 'is_negative': self._is_negative(credit)},
                {'name': '(%s)' % self.format_value(balance) if self._is_negative(balance) else self.format_value(balance), 'class': 'number', 'is_negative': self._is_negative(balance)},
            ],
            'colspan': 0,
            'level': 2 if self._context.get('print_mode', False) else 1
        }

        if self._context.get('print_mode', False):
            if not self._context.get('is_print_pdf', False):
                vals['columns'].insert(0, {'name': '%s %s' % (account.code, account.name)})
                vals['columns'].insert(2, {'name': _('Total')})
            else:
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].insert(1, {'name': _('Total')})
        return vals

    @api.model
    def _get_initial_balance_line(self, options, account, amount_currency, debit, credit, balance):
        vals = {
            'id': 'initial_%d' % account.id,
            'class': 'o_account_reports_initial_balance',
            'name': _('Initial Balance') if not self._context.get('is_print_pdf', False) else '%s %s' % (
                account.code, account.name),
            'parent_id': 'account_%d' % account.id,
            'columns': [
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': '(%s)' % self.format_value(debit) if self._is_negative(debit) else self.format_value(debit), 'class': 'number', 'is_negative': self._is_negative(debit)},
                {'name': '(%s)' % self.format_value(credit) if self._is_negative(credit) else self.format_value(credit), 'class': 'number', 'is_negative': self._is_negative(credit)},
                {'name': '(%s)' % self.format_value(balance) if self._is_negative(balance) else self.format_value(balance), 'class': 'number', 'is_negative': self._is_negative(balance)},
            ],
            'colspan': 0,
            'level': 2 if self._context.get('print_mode', False) else 1
        }
        if self._context.get('print_mode', False):
            if not self._context.get('is_print_pdf', False):
                vals['columns'].insert(0, {'name': '%s %s' % (account.code, account.name)})
                vals['columns'].insert(2, {'name': _('Initial Balance')})
            else:
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].insert(1, {'name': _('Initial Balance')})
        return vals

    @api.model
    def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')

        name = '%s %s' % (account.code, account.name)
        if len(name) > 40 and not self._context.get('print_mode'):
            name = name[:40] + '...'
        vals = {
            'id': 'account_%d' % account.id,
            'name': name,
            'title_hover': name,
            'columns': [
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': '(%s)' % self.format_value(debit) if self._is_negative(debit) else self.format_value(debit), 'class': 'number', 'is_negative': self._is_negative(debit)},
                {'name': '(%s)' % self.format_value(credit) if self._is_negative(credit) else self.format_value(credit), 'class': 'number', 'is_negative': self._is_negative(credit)},
                {'name': '(%s)' % self.format_value(balance) if self._is_negative(balance) else self.format_value(balance), 'class': 'number', 'is_negative': self._is_negative(balance)},
            ],
            'level': 2,
            'unfoldable': has_lines,
            'unfolded': has_lines and 'account_%d' % account.id in options.get('unfolded_lines') or unfold_all,
            'colspan': 0,
        }

        if self._context.get('print_mode', False):
            if not self._context.get('is_print_pdf', False):
                vals['columns'].insert(0, {'name': name})
                vals['columns'].insert(1, {'name': ''})
            else:
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
        return vals

    def print_xlsx(self, options):
        options.update({
            'is_print_excel': True
        })
        return super(AccountGeneralLedgerReport, self).print_xlsx(options)

    @api.model
    def _get_query_amls(self, options, expanded_account, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_account:    The account.account record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''

        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._force_strict_range(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self._get_query_currency_table(options)
        query = '''
                SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.analytic_tags_name,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    account_move_line__move_id.name         AS move_name,
                    company.currency_id                     AS company_currency_id,
                    partner.name                            AS partner_name,
                    account_move_line__move_id.type         AS move_type,
                    account.code                            AS account_code,
                    account.name                            AS account_name,
                    journal.code                            AS journal_code,
                    journal.name                            AS journal_name,
                    full_rec.name                           AS full_rec_name,
                    analytic_account.code                   AS analytic_account_name
                FROM account_move_line
                LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_analytic_account analytic_account           ON analytic_account.id = account_move_line.analytic_account_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE %s
                ORDER BY account_move_line.date, account_move_line.id
            ''' % (ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name()[:31])
        sheet.set_margins(top=0.92)
        super_columns = self._get_super_columns(options)
        header = super_columns['header']
        sheet.set_header(header)
        sheet.repeat_rows(first_row=0)
        date_default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 0, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'font_color': '#666666', 'num_format': 'mm/dd/yyyy'})
        default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'font_color': '#666666', 'indent': 0})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'font_color': '#666666'})
        specific_type = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'font_color': '#FF0000'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        report_name_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'align': 'center', 'font_size': 14})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center', 'font_size': 12})

        # Set the first column width to 50
        sheet.set_column(0, 0, 50)
        y_offset = 0
        for row in self.with_context(print_mode=True).get_header(options):
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update({'no_format': False, 'print_mode': True, 'prefetch_fields': False})
        # deactivating the prefetching saves ~35% on get_lines running time
        lines = self.with_context(ctx)._get_lines(options)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        # write all data rows
        for y in range(0, len(lines)):
            style = default_style
            col1_style = default_col1_style

            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                col1_style.set_bold(False)
                if cell_value and '\n' in cell_value:
                    cell_value = cell_value.replace('\n', '')
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            # write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value,
                                         date_default_style)
                else:
                    if cell_value and '\n' in cell_value:
                        cell_value = cell_value.replace('\n', '')
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, specific_type if lines[y]['columns'][x - 1].get('is_negative', False) else style)
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file

    def get_pdf(self, options, minimal_layout=True):
        # As the assets are generated during the same transaction as the rendering of the
        # templates calling them, there is a scenario where the assets are unreachable: when
        # you make a request to read the assets while the transaction creating them is not done.
        # Indeed, when you make an asset request, the controller has to read the `ir.attachment`
        # table.
        # This scenario happens when you want to print a PDF report for the first time, as the
        # assets are not in cache and must be generated. To workaround this issue, we manually
        # commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }

        body = self.env['ir.ui.view'].render_template(
            "account_reports.print_template",
            values=dict(rcontext),
        )
        body_html = self.with_context(print_mode=True, is_print_pdf=True).get_html(options)

        body = body.replace(b'<body class="o_account_reports_body_print">',
                            b'<body class="o_account_reports_body_print">' + body_html)
        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report'].render_template("phd_account_reports.general_leager_expanded_footer", values=rcontext)
            spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report'].render_template("web.minimal_layout",
                                                                   values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                'css': '',
                'o': self.env.user,
                'res_company': self.env.company,
            })
            header = self.env['ir.actions.report'].render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8')  # Ensure that headers and footer are correctly encoded
            spec_paperformat_args = {}
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)
                match_klass = "//div[contains(concat(' ', normalize-space(@class), ' '), ' {} ')]"

                for node in root.xpath(match_klass.format('header')):
                    headers = lxml.html.tostring(node)
                    headers = self.env['ir.actions.report'].render_template("web.minimal_layout",
                                                                            values=dict(rcontext, subst=True,
                                                                                        body=headers))

                for node in root.xpath(match_klass.format('footer')):
                    footer = lxml.html.tostring(node)
                    footer = self.env['ir.actions.report'].render_template("web.minimal_layout",
                                                                           values=dict(rcontext, subst=True,
                                                                                       body=footer))

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = False

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args
        )

    @api.model
    def _get_total_line(self, options, debit, credit, balance):
        vals = {
            'id': 'general_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': [
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': ''},
                {'name': '(%s)' % self.format_value(debit) if self._is_negative(debit) else self.format_value(debit), 'class': 'number', 'is_negative': self._is_negative(debit)},
                {'name': '(%s)' % self.format_value(credit) if self._is_negative(credit) else self.format_value(credit), 'class': 'number', 'is_negative': self._is_negative(credit)},
                {'name': '(%s)' % self.format_value(balance) if self._is_negative(balance) else self.format_value(balance), 'class': 'number', 'is_negative': self._is_negative(balance)},
            ],
            'colspan': 0,
        }
        if self._context.get('print_mode', False):
            if not self._context.get('is_print_pdf', False):
                vals['columns'].insert(0, {'name': _('Total')})
                vals['columns'].insert(1, {'name': ''})
            else:
                vals['columns'].pop(0)
                vals['columns'].pop(0)
                vals['columns'].pop(0)
        return vals

        ####################################################
        # OPTIONS: Account Type
        ####################################################

    @api.model
    def _init_filter_account_type(self, options, previous_options=None):
        previous_account_type = (previous_options or {}).get('account_types', [])
        account_type_ids = [int(x) for x in previous_account_type]
        selected_account_type = self.env['account.account.type'].search(
            [('id', 'in', account_type_ids)])
        options['account_types'] = selected_account_type.ids
        options['selected_account_type_names'] = selected_account_type.mapped('name')

    def get_report_informations(self, options):
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name
                                                          for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in
                                                      options['analytic_tags']]
        if options.get('account_types') is not None:
            options['selected_account_type_names'] = [self.env['account.account.type'].browse(int(account)).name
                                                      for account in options['account_types']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in
                                               options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for
                                                      category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(
                        journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view'].render_template(
                    self._get_templates().get('search_template', 'account_report.search_template'),
                    values=searchview_dict),
                }
        return info

    @api.model
    def _get_options_account_type_domain(self, options):
        domain = []
        if options.get('account_types'):
            account_type_ids = [int(acc) for acc in options['account_types']]
            domain.append(('account_type_id', 'in', account_type_ids))
        return domain

    @api.model
    def _get_options_domain(self, options):
        domain = super(AccountGeneralLedgerReport, self)._get_options_domain(options)
        domain += self._get_options_account_type_domain(options)
        return domain
