from odoo import models, fields, api


class ReleasedFund(models.Model):
    _name = 'released.fund'
    _description = 'Released Fund'

    def _get_default_currency_id(self):
        return self.env.company.currency_id.id

    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain="[('type', '=', 'bank')]")
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id)

    date = fields.Date('Date', required=True)
    name = fields.Char('Number')
    amount = fields.Monetary('Amount')
    transit_account_id = fields.Many2one('account.account', string='Transit Account', required=True)
    is_reconciled = fields.Boolean(string='Reconciled')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled')
    ], string='State', default='draft')

    move_ids = fields.One2many('account.move', 'released_fund_id', string='Journal Entries')
    move_count = fields.Integer(compute='_compute_move_count')

    def _compute_move_count(self):
        for record in self:
            record.move_count = len(record.move_ids)

    def _prepare_entry_values(self):
        self.ensure_one()

        return {
            'date': self.date,
            'journal_id': self.journal_id.id,
            'released_fund_id': self.id,
        }

    def _prepare_item_values(self):
        def prepare_bank_line():
            return {
                'account_id': self.journal_id.default_debit_account_id.id,
                'debit': self.amount,
                'credit': 0,
            }

        def prepare_transit_line():
            return {
                'account_id': self.transit_account_id.id,
                'debit': 0,
                'credit': self.amount,
            }

        self.ensure_one()

        return [
            (0, 0, prepare_bank_line()),
            (0, 0, prepare_transit_line()),
        ]

    def create_journal_entry(self):
        values_lst = []

        for record in self.filtered(lambda r: r.state == 'draft'):
            entry = record._prepare_entry_values()
            entry['line_ids'] = record._prepare_item_values()
            values_lst.append(entry)

        moves = self.env['account.move'].sudo().create(values_lst)
        moves.with_context(is_post=True).action_post()

    def action_confirm(self):
        self = self.filtered(lambda r: r.state == 'draft')
        self.create_journal_entry()
        self.update({'state': 'confirm'})

    def action_draft(self):
        # Cancel all linked journal entries, then set state to draft
        posted_moves = self.mapped('move_ids').filtered(lambda r: r.state == 'posted')
        posted_moves.button_draft()
        posted_moves.button_cancel()

        self.write({
            'state': 'draft'
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel'
        })

    def action_view_entry(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action.pop('context')
        action.pop('domain')

        moves = self.mapped('move_ids')
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
