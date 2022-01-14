import json
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from .paypal_request import PaypalRequest, PaypalError


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
