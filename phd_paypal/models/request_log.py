from odoo import api, models, fields, _


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

    def action_view_entry(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action.pop('context')
        action.pop('domain')

        moves = self.mapped('paypal_transaction_ids').mapped('move_ids')
        if len(moves) > 1:
            action['domain'] = [('id', 'in', moves.ids)]
        elif moves:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = moves.id

        return action
