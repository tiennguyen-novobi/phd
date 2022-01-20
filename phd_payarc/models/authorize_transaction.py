from odoo import models, fields, api


class AuthorizeTransaction(models.Model):
    _name = 'authorize.transaction'
    _description = 'Authorize.Net Transaction'

    batch_report_id = fields.Many2one('payarc.batch.report', string='PayArc Batch Report')
