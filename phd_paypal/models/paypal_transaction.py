import json
import logging

from datetime import datetime, timedelta

from odoo import fields, models, api, _
from .paypal_request import PaypalRequest, PaypalError

_logger = logging.getLogger(__name__)


class PaypalTransaction(models.Model):
    _name = 'paypal.transaction'
    _description = 'Paypal Transaction'
    _rec_name = 'transaction_id'

    transaction_id = fields.Char(string='Transaction ID')
    date = fields.Date(string='Date')
    order_id = fields.Char(string='DTC Order ID')
    authorization_id = fields.Char(string='Authorization ID')
    amount = fields.Float(string='Amount')
    paypal_fee_amount = fields.Float(string='Paypal Fee Amount')

    log_id = fields.Many2one('request.log', string='Log')

    # Only one record
    move_ids = fields.One2many('account.move', 'paypal_transaction_id', string='Journal Entries')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], compute='_compute_state', store=True)

    @api.depends('move_ids')
    def _compute_state(self):
        for record in self:
            record.state = 'done' if record.move_ids else 'draft'

    @api.model
    def create_jobs_for_synching(self, vals, update=False, record=False):
        return self._sync_in_queue_job(vals, update, record)

    @api.model
    def _sync_in_queue_job(self, vals, update, record):
        if update:
            record.with_context(for_synching=True).write(vals)
        else:
            record = self.with_context(for_synching=True).create(vals)
        return record

    @api.model
    def run(self):
        from_date = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = from_date
        self.get_paypal_transaction_via_braintree(from_date, to_date)

    @api.model
    def process_paypal_transaction(self, transactions):
        paypal_transactions = self.env['paypal.transaction'].browse()
        for transaction in transactions:
            record = self.sudo().search([('transaction_id', '=', transaction['transaction_id'])], limit=1)
            # If a record is already existed
            existed_record = True if record else False

            paypal_transaction = self.create_jobs_for_synching(vals=transaction, update=existed_record, record=record)
            paypal_transactions |= paypal_transaction
        return paypal_transactions

    @api.model
    def get_paypal_transaction_via_braintree(self, settled_date_from, settled_date_to):
        ir_params_sudo = self.env['ir.config_parameter'].sudo()
        credentials = {
            'merchant_id': ir_params_sudo.get_param('braintree_merchant_id'),
            'public_key': ir_params_sudo.get_param('braintree_public_key'),
            'private_key': ir_params_sudo.get_param('braintree_private_key')
        }
        paypal_client = PaypalRequest(credentials)
        try:
            res = paypal_client.get_transaction_by_date(settled_date_from)
            paypal_transactions = self.process_paypal_transaction(res)
            self.env['request.log'].create({
                'from_date': settled_date_from,
                'to_date': settled_date_to,
                'res_model': 'paypal.transaction',
                'status': 'done',
                'is_resolved': True,
                'datas': json.dumps({'data': res}, indent=2),
                'paypal_transaction_ids': [(6, 0, paypal_transactions.ids)]
            })
            paypal_transactions.create_journal_entry()
        except PaypalError as e:
            self.env['request.log'].create({
                'from_date': settled_date_from,
                'to_date': settled_date_to,
                'res_model': 'paypal.transaction',
                'status': 'failed',
                'message': e,
            })
        except Exception as e:
            self.env.cr.rollback()
            self.env['request.log'].create({
                'from_date': settled_date_from,
                'to_date': settled_date_to,
                'res_model': 'paypal.transaction',
                'status': 'failed',
                'datas': json.dumps({'data': res}, indent=2),
                'message': e,
            })

    def _prepare_entry_values(self, company):
        self.ensure_one()

        return {
            'date': self.date,
            'ref': "Order: {} | Transaction ID: {} | Auth ID: {}".format(self.order_id, self.transaction_id, self.authorization_id),
            'journal_id': company.paypal_journal_id.id,
            'x_studio_dtc_order_id': self.order_id,
            'x_studio_transaction_id': self.transaction_id,
            'x_studio_authorization_id': self.authorization_id,
            'x_studio_merchant': company.paypal_merchant,
        }

    def _prepare_item_values(self, company, entry=None):
        def prepare_sales_line():
            return {
                'account_id': company.paypal_sales_account_id.id,
                'partner_id': False,
                'name': label,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': [(6, 0, analytic_tags.ids)],
                'debit': 0,
                'credit': self.amount,
            }

        def prepare_fees_line():
            return {
                'account_id': company.paypal_fee_account_id.id,
                'partner_id': company.paypal_partner_id.id,
                'name': label,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': [(6, 0, analytic_tags.ids)],
                'debit': self.paypal_fee_amount,
                'credit': 0,
            }

        def prepare_bank_line():
            return {
                'account_id': company.paypal_bank_account_id.id,
                'partner_id': False,
                'name': label,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': [(6, 0, analytic_tags.ids)],
                'debit': self.self.amount - self.paypal_fee_amount,
                'credit': 0,
            }


        self.ensure_one()
        label = (entry or {}).get('ref', False)
        analytic_account = company.paypal_analytic_account_id,
        analytic_tags = company.paypal_analytic_tag_ids,

        return [
            (0, 0, prepare_sales_line()),
            (0, 0, prepare_fees_line()),
            (0, 0, prepare_bank_line())
        ]

    def create_journal_entry(self):
        values_lst = []

        # We don't need to handle multi-companies case here
        company = self.env.user.company_id

        if not company.paypal_journal_id:
            _logger.error('Cannot process journal entries from Paypal Transactions due to missing config for Journal!')
            return

        for record in self.filtered('authorization_id'):
            entry = record._prepare_entry_values(company)
            entry['line_ids'] = record._prepare_item_values(company, entry)
            values_lst.append(entry)

        moves = self.env['account.move'].sudo().create(values_lst)
        moves.action_post()

    def action_view_entry(self):
        self.ensure_one()
        if not self.move_ids:
            return

        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_ids.id,
            'view_mode': 'form',
            'target': 'main',
        }
