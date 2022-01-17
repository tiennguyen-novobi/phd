from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    payarc_batch_id = fields.Many2one('payarc.batch.report', string='PayArc Batch Report')
