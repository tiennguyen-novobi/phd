# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import safe_eval
from psycopg2._psycopg import AsIs


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_tags_name = fields.Char(compute='_compute_analytic_tags_name', store=True)
    account_type_id = fields.Many2one('account.account.type', related='account_id.user_type_id', store=True)
    phd_communication = fields.Char(compute='_compute_phd_communication', store=True)

    @api.depends('move_id.name', 'move_id.state')
    def _compute_phd_communication(self):
        for record in self:
            record.phd_communication = False
            if record.account_id.id == record.company_id.general_ledger_delivered_account.id:
                if record.product_id and record.move_id.stock_move_id and record.move_id.stock_move_id._is_out():
                    record.phd_communication = record._generate_phd_communication_for_delivery_order()
                if not record.phd_communication and record.product_id and record.move_id.type == 'out_invoice':
                    record.phd_communication = record._generate_phd_communication_for_ap_invoice()
            if record.credit_card_charges_payment_id and record.is_credit_card_charges:
                record.phd_communication = record._generate_phd_communication_for_credit_card_move_line()

    def _generate_phd_communication_for_ap_invoice(self):
        self.ensure_one()
        data = []
        communication = False
        sale_order_id = self.move_id.invoice_line_ids.mapped('sale_line_ids.order_id')
        if sale_order_id:
            data.append(self.move_id.name)
            picking_ids = sale_order_id.mapped('picking_ids').filtered(
                lambda x: self.product_id.id in x.move_line_ids.mapped('product_id').ids and x.state == 'done')
            if picking_ids:
                data.append(','.join(picking_ids.mapped('name')))
            data.append(self.product_id.default_code)
            if self.move_id.ref:
                data.append("PO# %s" % self.move_id.ref)
            data.append("SO# %s" % sale_order_id.name)
        if data:
            communication = ' | '.join(data)
        return communication

    def _generate_phd_communication_for_delivery_order(self):
        self.ensure_one()
        return '%s | %s | %s | SO# %s' % (
            self.move_id.name, self.move_id.stock_move_id.picking_id.name, self.product_id.default_code,
            self.move_id.stock_move_id.origin)

    def _generate_phd_communication_for_credit_card_move_line(self):
        self.ensure_one()
        phd_description = False
        values = []
        payment_id = self.credit_card_charges_payment_id
        if payment_id:
            if payment_id.appears_on_statement_as:
                values.append(payment_id.appears_on_statement_as)
            if self.name:
                values.append(self.name)
            if payment_id.communication:
                values.append(payment_id.communication)
            if payment_id.partner_card_holder_id:
                values.append(payment_id.partner_card_holder_id.name)
            if payment_id.credit_card_transaction_id:
                values.append(payment_id.credit_card_transaction_id)
        if values:
            phd_description = ' | '.join(values)
        return phd_description

    @api.depends('analytic_tag_ids')
    def _compute_analytic_tags_name(self):
        for record in self:
            record.analytic_tags_name = ', '.join(record.analytic_tag_ids.mapped('name'))

    def _get_analytic_domain(self, options):
        """
        Copy from _query_get of model account.move.line of account module
        :param options:
        :type options: dict
        :return:
        """
        domain = []
        date_field = 'date'
        if options.get('aged_balance'):
            date_field = 'date_maturity'
        if options.get('date_to'):
            domain += [(date_field, '<=', options['date_to'])]
        if options.get('date_from'):
            if not options.get('strict_range'):
                domain += ['|', (date_field, '>=', options['date_from']),
                           ('account_id.user_type_id.include_initial_balance', '=', True)]
            elif options.get('initial_bal'):
                domain += [(date_field, '<', options['date_from'])]
            else:
                domain += [(date_field, '>=', options['date_from'])]

        if options.get('journal_ids'):
            domain += [('journal_id', 'in', options['journal_ids'])]

        state = options.get('state')
        if state and state.lower() != 'all':
            domain += [('move_id.state', '=', state)]

        if options.get('company_id'):
            domain += [('company_id', '=', options['company_id'])]

        if 'company_ids' in options:
            domain += [('company_id', 'in', options['company_ids'])]

        if options.get('reconcile_date'):
            domain += ['|', ('reconciled', '=', False), '|',
                       ('matched_debit_ids.max_date', '>', options['reconcile_date']),
                       ('matched_credit_ids.max_date', '>', options['reconcile_date'])]

        if options.get('account_tag_ids'):
            domain += [('account_id.tag_ids', 'in', options['account_tag_ids'].ids)]

        if options.get('account_ids'):
            domain += [('account_id', 'in', options['account_ids'].ids)]

        if options.get('partner_ids'):
            domain += [('partner_id', 'in', options['partner_ids'].ids)]

        if options.get('partner_categories'):
            domain += [('partner_id.category_id', 'in', options['partner_categories'].ids)]

        if domain:
            domain.append(('display_type', 'not in', ('line_section', 'line_note')))
            domain.append(('move_id.state', '!=', 'cancel'))

        return domain

    @api.model
    def _query_get(self, domain=None):
        context = dict(self._context or {})
        # If the report based on analytic line and analytic account filter is used, query on the Analytic Line
        # else using origin Odoo report
        if context.get('analytic_report') and context.get('analytic_account_ids'):
            self.check_access_rights('read')
            domain = domain or []
            if not isinstance(domain, (list, tuple)):
                domain = safe_eval(domain)

            domain += self._get_analytic_domain(context)

            if domain:
                query = self._where_calc(domain)
                # Join the account move line with analytic line table, filter by analytic account
                query.add_join(("account_move_line", "account_analytic_line", "id", "move_id", "analytic_line"),
                               implicit=False,
                               outer=False,
                               extra='"{rhs}"."account_id" in (%s)',
                               extra_params=[
                                   AsIs(','.join(str(acc_id) for acc_id in context['analytic_account_ids'].ids))]
                               )
                if context.get('analytic_tag_ids'):
                    # Join the account analytic line with tag table, filter by analytic tag
                    query.add_join((
                        "account_move_line__analytic_line", "account_analytic_line_tag_rel", "id", "line_id",
                        "tag_id"),
                        implicit=False,
                        outer=False,
                        extra='"{rhs}"."tag_id" in (%s)',
                        extra_params=[
                            AsIs(','.join(str(tag_id) for tag_id in context['analytic_tag_ids'].ids))]
                    )
                tables, where_clause, where_clause_params = query.get_sql()
        else:
            tables, where_clause, where_clause_params = super(AccountMoveLine, self)._query_get(domain)
        return tables, where_clause, where_clause_params
