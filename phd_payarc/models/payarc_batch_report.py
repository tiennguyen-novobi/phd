import json
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from .payarc_request import PayarcRequest, PayarcError


class PayarcBatchReport(models.Model):
    _name = 'payarc.batch.report'
    _description = 'PayArc Batch Report'
    _rec_name = 'batch_ref'

    journal_id = fields.Many2one('account.journal', string='Journal', domain="[('type', '=', 'bank')]")
    date = fields.Date(string='Batch Date')
    amount = fields.Float(string='Amount')
    transaction_qty = fields.Integer(string='# of Transactions')
    batch_ref = fields.Char(string='Batch Ref')
    fees_amount = fields.Float(string='Fees')
    reserve_hold_amount = fields.Float(string='Reserve Hold')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('post', 'Posted'),
        ], string='State', default='draft')
    settlement_id = fields.Many2one('settlement.report', string='Settlement')

    sales_account_id = fields.Many2one('account.account', string='Sales Account', domain="[('deprecated', '=', False)]")
    fees_account_id = fields.Many2one('account.account', string='Fees Account', domain="[('deprecated', '=', False)]")
    reserve_account_id = fields.Many2one('account.account', string='Reserve Account', domain="[('deprecated', '=', False)]")
    transit_account_id = fields.Many2one('account.account', string='Transit Account', domain="[('deprecated', '=', False)]")

    @api.depends('amount', 'fees_amount', 'reserve_hold_amount')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.amount - record.fees_amount - record.reserve_hold_amount

    def confirm(self):
        self.update({'state': 'post'})

    @api.model
    def process_batch_report_from_payarc(self, batch_report_datas):
        batch_reports = self.browse()
        for batch_report in batch_report_datas:
            record = self.sudo().search([('batch_ref', '=', batch_report['batch_ref'])], limit=1)
            # If a record is already existed
            existed_record = True if record else False

            batch_reports |= self.create_jobs_for_synching(vals=batch_report, update=existed_record, record=record)
        return batch_reports

    @api.model
    def run(self):
        from_date = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = from_date
        self.get_batch_from_payarc(from_date, to_date)

    @api.model
    def _extend_information_for_batch_report(self, datas, journal):
        for data in datas:
            data.update({
                'journal_id': journal.id,
                'sales_account_id': journal.payarc_sales_account_id.id,
                'fees_account_id': journal.payarc_fees_account_id.id,
                'reserve_account_id': journal.payarc_reserve_account_id.id,
                'transit_account_id': journal.payarc_transit_account_id.id
            })
        return datas

    @api.model
    def get_batch_from_payarc(self, from_date, to_date):
        integrated_journals = self.env['account.journal'].search([('is_integrate_with_payarc', '=', True)])
        for journal in integrated_journals:
            payarc_info = {
                'payarc_access_token': journal.payarc_access_token
            }
            processer = PayarcRequest(payarc_info)
            try:
                res = processer.get_batch_from_payarc(from_date, to_date)
                batch_report_datas = self._extend_information_for_batch_report(res, journal)
                payarc_batch_reports = self.process_batch_report_from_payarc(batch_report_datas)
                self.env['request.log'].create({
                    'from_date': from_date,
                    'to_date': to_date,
                    'res_model': 'payarc.batch.report',
                    'status': 'done',
                    'is_resolved': True,
                    'payarc_batch_report_ids': [(6, 0, payarc_batch_reports.ids)],
                    'datas': json.dumps({'data': res}, indent=2)
                })
            except PayarcError as e:
                self.env['request.log'].create({
                    'from_date': from_date,
                    'to_date': to_date,
                    'res_model': 'payarc.batch.report',
                    'status': 'failed',
                    'message': e,
                })
            except Exception as e:
                self.env.cr.rollback()
                self.env['request.log'].create({
                    'from_date': from_date,
                    'to_date': to_date,
                    'res_model': 'payarc.batch.report',
                    'status': 'failed',
                    'message': e,
                    'datas': json.dumps({'data': res}, indent=2)
                })

    @api.model
    def create_jobs_for_synching(self, vals, update=False, record=False):
        """
        :param vals_list:
        :param channel_id:
        :return:
        """
        return self._sync_in_queue_job(vals, update, record)

    @api.model
    def _sync_in_queue_job(self, vals, update, record):
        if update:
            record.with_context(for_synching=True).write(vals)
        else:
            record = self.with_context(for_synching=True).create(vals)
        return record
