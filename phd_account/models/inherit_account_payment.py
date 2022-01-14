# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_deposit_customization = fields.Boolean()
    phd_payment_deposit_ids = fields.One2many('phd.payment.deposit', 'payment_id')
    total_deposit_amount = fields.Monetary(compute='_compute_total_deposit_amount')
    custom_journal_id = fields.Many2one('account.journal', string='Journal',
                                        readonly=True, states={'draft': [('readonly', False)]})
    is_credit_card_charges = fields.Boolean()
    credit_card_holder_id = fields.Many2one('res.partner')
    credit_card_transaction_id = fields.Char(string='Transaction ID')
    appears_on_statement_as = fields.Char(string='Appears on Statement As')
    partner_card_holder_id = fields.Many2one('res.partner', string='Card Holder')
    extended_details = fields.Char(string='Extended Details')

    @api.model
    def load_views(self, views, options=None):
        res = super(AccountPayment, self).load_views(views, options=options)
        if self.env.context.get('default_is_credit_card_charges', False) and self.env.context.get('default_payment_type', False):
            if 'fields_views' in res and 'form' in res['fields_views'] and 'fields' in res['fields_views']['form'] and 'journal_id' in res['fields_views']['form']['fields']:
                res['fields_views']['form']['fields']['journal_id'].update({
                    'context': {
                        'is_credit_card_charge': True,
                        'default_payment_type': self.env.context.get('default_payment_type')
                    },
                })
        return res

    @api.depends('phd_payment_deposit_ids', 'phd_payment_deposit_ids.price_subtotal')
    def _compute_total_deposit_amount(self):
        for record in self:
            if record.phd_payment_deposit_ids:
                record.total_deposit_amount = sum(line.price_subtotal for line in record.phd_payment_deposit_ids)
            else:
                record.total_deposit_amount = 0.0

    def post_deposit(self):
        self.ensure_one()
        if self.total_deposit_amount <= 0:
            raise ValidationError(_('Payment Amount must be greater than 0'))
        if self and self.is_deposit_customization:
            AccountMove = self.env['account.move'].with_context(default_type='entry')
            # keep the name in case of a payment reset to draft
            if not self.name:
                # Use the right sequence to set the name
                if self.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if self.partner_type == 'customer':
                        if self.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if self.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if self.partner_type == 'supplier':
                        if self.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if self.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                self.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=self.payment_date)
                if not self.name and self.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))
            AccountMove.create(self._prepare_payment_deposit_moves())
        if self.move_line_ids:
            self.move_line_ids[0].move_id.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()
            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(self.move_line_ids[0].move_id.mapped('name'))
            self.write({'state': 'posted', 'move_name': move_name})

    def _prepare_payment_deposit_moves(self):
        if self.payment_type == 'outbound':
            liquidity_line_account = self.journal_id.default_debit_account_id
        else:
            liquidity_line_account = self.journal_id.default_credit_account_id

        move_vals = {
            'date': self.payment_date,
            'ref': self.communication,
            'journal_id': self.custom_journal_id.id if not self.is_credit_card_charges else self.journal_id.id,
            'currency_id': self.custom_journal_id.currency_id.id or self.company_id.currency_id.id,
            'partner_id': self.partner_id.id,
            'line_ids': [],
        }
        # Liquidity line.
        liquidity_line_values = {
            'name': self.name,
            'amount_currency': 0.0,
            'currency_id': False,
            'credit_card_charges_payment_id': self.id,
            'is_credit_card_charges': self.is_credit_card_charges,
            'date_maturity': self.payment_date,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'account_id': liquidity_line_account.id,
            'payment_id': self.id,
        }
        if self.is_credit_card_charges and self.partner_type == 'supplier':
            liquidity_line_values.update({
                'debit': self.total_deposit_amount if self.payment_type == 'inbound' else 0.0,
                'credit': self.total_deposit_amount if self.payment_type == 'outbound' else 0.0,
            })
        else:
            liquidity_line_values.update({
                'debit': self.total_deposit_amount if self.partner_type == 'customer' else 0.0,
                'credit': self.total_deposit_amount if self.partner_type == 'supplier' else 0.0,
            })
        move_vals.get('line_ids').append((0, 0, liquidity_line_values))

        for line in self.phd_payment_deposit_ids:
            vals = {
                'name': line.description,
                'amount_currency': 0.0,
                'currency_id': False,
                'credit_card_charges_payment_id': self.id,
                'is_credit_card_charges': self.is_credit_card_charges,
                'analytic_account_id': line.analytic_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                'debit': line.price_subtotal if self.partner_type == 'supplier' else 0.0,
                'credit': line.price_subtotal if self.partner_type == 'customer' else 0.0,
                'date_maturity': self.payment_date,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'account_id': line.account_id.id,
                'payment_id': self.id,
            }
            if self.is_credit_card_charges and self.partner_type == 'supplier':
                vals.update({
                    'debit': line.price_subtotal if self.payment_type == 'outbound' else 0.0,
                    'credit': line.price_subtotal if self.payment_type == 'inbound' else 0.0,
                })
            else:
                vals.update({
                    'debit': line.price_subtotal if self.partner_type == 'supplier' else 0.0,
                    'credit': line.price_subtotal if self.partner_type == 'customer' else 0.0,
                })
            move_vals.get('line_ids').append((0, 0, vals))

        return move_vals

    def post(self):
        is_deposit_customization = False
        for record in self:
            if record.is_deposit_customization:
                is_deposit_customization = True
                record.post_deposit()
        if not is_deposit_customization:
            res = super(AccountPayment, self).post()
            return res
