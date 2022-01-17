from odoo import api, models, fields, api


class RequestLog(models.Model):
    _inherit = 'request.log'

    paypal_transaction_ids = fields.One2many('paypal.transaction', 'log_id', string='Paypal Transactions')
    transaction_count = fields.Integer(compute='_compute_transaction_count')
    paypal_entries_count = fields.Integer(compute='_compute_transaction_count')

    @api.depends('res_model', 'paypal_transaction_ids')
    def _compute_transaction_count(self):
        for record in self:
            record.transaction_count = len(record.paypal_transaction_ids)
            record.paypal_entries_count = len(record.paypal_transaction_ids.mapped('move_ids'))

    def action_open_details(self):
        if self.res_model == 'paypal.transaction':
            action = self.env.ref('phd_paypal.phd_paypal_transaction_action').read()[0]
            if len(self.paypal_transaction_ids) > 0:
                action['domain'] = [('id', 'in', self.paypal_transaction_ids.ids)]
            return action
        return super().action_open_details()

    def action_open_paypal_entries(self):
        self.ensure_one()

        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': [('id', 'in', record.paypal_transaction_ids.mapped('move_ids').ids)],
            'view_mode': 'tree',
            'target': 'current',
        }
