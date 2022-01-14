from odoo import api, models, fields, api


class RequestLog(models.Model):
    _inherit = 'request.log'

    payarc_batch_report_ids = fields.Many2many('payarc.batch.report', string='PayArc Batch Reports')
    batch_report_count = fields.Integer(compute='_compute_batch_report_count')

    @api.depends('res_model', 'payarc_batch_report_ids')
    def _compute_batch_report_count(self):
        for record in self:
            record.batch_report_count = len(record.payarc_batch_report_ids)

    def action_open_details(self):
        if self.res_model == 'payarc.batch.report':
            action = self.env.ref('phd_payarc.phd_batch_report_action').read()[0]
            if len(self.payarc_batch_report_ids) > 0:
                action['domain'] = [('id', 'in', self.payarc_batch_report_ids.ids)]
            return action
        return super().action_open_details()
