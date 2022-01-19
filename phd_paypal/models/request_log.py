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
        self.ensure_one()
        tree_view_id = self.env.ref('account.view_move_tree').id
        form_view_id = self.env.ref('account.view_move_line_form').id

        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.paypal_transaction_ids.mapped('move_ids').ids)],
            'target': 'current',
        }
