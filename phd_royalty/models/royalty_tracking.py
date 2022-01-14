# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

DAILY = 'daily'
MONTHLY = 'monthly'
YEARLY = 'yearly'

DRAFT = 'draft'
CONFIRM = 'confirm'
DONE = 'done'
CANCEL = 'cancel'


class RoyaltyTracking(models.Model):
    _name = "royalty.tracking"
    _description = 'Royalty Tracking Configuration'

    ###################################
    # FIELDS
    ###################################

    date_start = fields.Date(string='Period Begin', required=True, default=lambda self: datetime.now())
    date_end = fields.Date(stFring='Period End', required=True, copy=False)

    product_id = fields.Many2one('product.product', required=True)
    bill_frequency = fields.Selection([(DAILY, _('Daily')), (MONTHLY, _('Monthly')), (YEARLY, _('Yearly'))],
                                      required=True, default=MONTHLY)
    bill_schedule_date = fields.Date(string="Next Bill on", required=True, copy=False)

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term')

    royalty_tracking_line_ids = fields.One2many('royalty.tracking.line', 'royalty_tracking_id')

    royalty_info_ids = fields.One2many('royalty.info', 'royalty_tracking_id')

    state = fields.Selection([(DRAFT, _('Draft')), (CONFIRM, _('In Progress')), (DONE, _('Done')),
                              (CANCEL, _('Cancel'))], required=True, default=DRAFT)

    generated_bill = fields.One2many('account.move', 'royalty_tracking_id')

    ###################################
    # CONSTRAINTS
    ###################################
    @api.constrains('start_date', 'end_date', 'bill_schedule_date')
    def _check_date(self):
        date_now = datetime.now().date()
        if self.bill_schedule_date:
            if self.bill_schedule_date < date_now:
                raise ValidationError(_('Please select a bill date equal/or greater than the current date.'))
        if self.date_end:
            if self.date_end < date_now:
                raise ValidationError(_('Please select a period end equal/or greater than the current date.'))
        if self.date_start and self.date_end:
            if self.date_start > self.date_end:
                raise ValidationError(_("End Date of Period cannot be earlier than Start Date."))
            if self.bill_schedule_date:
                if self.bill_schedule_date > self.date_end or self.bill_schedule_date < self.date_start:
                    raise ValidationError(_("Next bill can't be schedule earlier or later the Period."))

    @api.constrains('royalty_info_ids')
    def _check_unique_royalty_info(self):
        for tracking in self:
            min_qty_lst = list(map(lambda info: info.min_qty, tracking.royalty_info_ids))
            if len(min_qty_lst) > len(set(min_qty_lst)):
                raise ValidationError(_('This Min Quantity has been set.'))

    @api.constrains('product_id')
    def _check_unique_product(self):
        for tracking in self:
            tracking_id = self.env['royalty.tracking'].search([('state', '=', CONFIRM),
                                                               ('product_id', '=', tracking.product_id.id)])
            if tracking_id:
                raise ValidationError(_('Product %s already exists in another tracking configuration.'
                                        % tracking.product_id.display_name))

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_start(self):
        self.ensure_one()
        self._action_start()
        self._check_company()
        return self.action_open_tracking_lines()

    def action_open_tracking_lines(self):
        self.ensure_one()
        domain = [('royalty_tracking_id', '=', self.id)]
        action = {
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('phd_royalty.royalty_tracking_line_tree_view').id, 'tree')],
            'view_mode': 'tree, form',
            'name': _('Royalty Tracking Lines'),
            'res_model': 'royalty.tracking.line',
            'domain': domain
        }
        return action

    @api.model
    def action_update_tracking(self):
        date_now = datetime.now().date()
        res = self.env['royalty.tracking'].search([('state', '=', CONFIRM)])
        for tracking in res:
            if tracking.date_end == date_now:
                tracking.write({
                    'state': DONE
                })
            # Generate bill
            if tracking.bill_schedule_date == date_now:
                last_tracking_line = tracking.royalty_tracking_line_ids[-1]
                royalty_tracking_line_ids = tracking.royalty_tracking_line_ids.filtered(
                    lambda line: not line.invoice_id
                                 and line.qty_consumed > 0
                                 and line.standard_price > 0)
                if royalty_tracking_line_ids:
                    invoice_vals = tracking._prepare_invoice()
                    line_vals = []
                    for line in royalty_tracking_line_ids:
                        line_vals.append(line._prepare_invoice_line())

                    invoice_vals['invoice_line_ids'] = [(0, 0, line) for line in line_vals]
                    invoice_id = self.env['account.move'].create(invoice_vals)
                    royalty_tracking_line_ids.write({
                        'invoice_id': invoice_id.id
                    })
                    tracking.bill_schedule_date = tracking.get_next_bill_schedule_date()
                last_tracking_line.write({
                    'date_end': date_now
                })

                self.env['royalty.tracking.line'].create({
                    'royalty_tracking_id': tracking.id,
                    'date_start': date_now,
                    'date_end': tracking.date_end,
                    'royalty_info_id': last_tracking_line.royalty_info_id.id
                })

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def get_next_bill_schedule_date(self):
        delta = False
        if self.bill_frequency == DAILY:
            delta = relativedelta(days=+1)
        elif self.bill_frequency == MONTHLY:
            delta = relativedelta(months=+1)
        elif self.bill_frequency == YEARLY:
            delta = relativedelta(years=+1)

        next_bill_schedule_date = delta and min(self.bill_schedule_date + delta, self.date_end)
        return next_bill_schedule_date

    def _prepare_invoice(self):
        self.ensure_one()
        company_id = self.env.user.company_id
        journal = self.env['account.move'].with_context(default_type='in_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting purchase journal for the company %s (%s).') % (
                company_id.name, company_id.id))

        invoice_vals = {
            'type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_id.id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': company_id.id,
        }
        return invoice_vals

    def _get_tracking_generate_bill_domain(self):
        domain = [('state', '=', CONFIRM), ('bill_schedule_date', '=', datetime.now().date)]
        return domain

    def _action_start(self):
        for tracking in self:
            if tracking.state != 'draft':
                continue
            if not tracking.royalty_tracking_line_ids:
                self.env['royalty.tracking.line'].create(tracking._prepare_tracking_lines_values())
                last_tracking_line = self.royalty_tracking_line_ids[-1]
                self.product_id.standard_price = last_tracking_line.standard_price
            tracking.write({
                'state': 'confirm',
            })

    def _prepare_tracking_lines_values(self):
        move_ids = self.env['stock.move'].search([('state', '=', 'done'),
                                                  ('date', '>=', self.date_start),
                                                  ('product_id', '=', self.product_id.id),
                                                  ('date', '<', self.date_end)], order='date asc')

        consumed_qty = 0

        info_lst_stack = self.royalty_info_ids.mapped(lambda rec: rec)

        vals = []
        line_vals = move_ids.mapped(lambda move: {
            'manufacture_date': move.date,
            'production_id': move.raw_material_production_id.id,
            'lot_id': move.lot_id.id,
            'purchase_id': move.raw_material_production_id.purchase_id.id,
            'partner_id': move.raw_material_production_id.purchase_id.partner_id.id,
            'product_id': move.product_id.id,
            'finished_product_id': move.raw_material_production_id.product_id.id,
            'product_uom_qty': move.product_uom_qty
        })
        vals.append({
            'royalty_tracking_id': self.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'royalty_info_id': info_lst_stack[0].id if info_lst_stack else False,
            'royalty_tracking_line_detail_ids': line_vals
        })

        if len(info_lst_stack) > 1:
            date_end = move_ids[0].date if move_ids else False
            previous_index = 0
            index = 0
            info_start = info_end = info_lst_stack[0]
            info_lst_stack -= info_start
            if info_start.min_qty <= 0:
                info_end = info_lst_stack[0]
                info_lst_stack -= info_end

            while index < len(line_vals) and info_end:
                line_val = line_vals[index]
                consumed_qty += line_val['product_uom_qty']
                if consumed_qty >= info_end.min_qty:
                    min_qty = info_end.min_qty
                    new_line_vals = line_val.copy()
                    old_consumed_qty = consumed_qty - line_val['product_uom_qty']
                    new_line_qty = min_qty - old_consumed_qty - 1

                    consumed_qty = min_qty - 1
                    new_line_vals['product_uom_qty'] = new_line_qty
                    line_vals[index]['product_uom_qty'] = line_val['product_uom_qty'] - new_line_qty
                    vals[-1].update({
                        'date_end': date_end,
                        'royalty_tracking_line_detail_ids': line_vals[previous_index: index] + [new_line_vals],
                    })
                    previous_index = index
                    vals.append({
                        'royalty_tracking_id': self.id,
                        'date_start': date_end,
                        'date_end': self.date_end,
                        'royalty_info_id': info_end.id,
                        'royalty_tracking_line_detail_ids': line_vals[index:]
                    })
                    index -= 1
                    info_end = info_lst_stack and info_lst_stack[0]
                    info_lst_stack -= info_end

                index += 1
                date_end = line_val['manufacture_date']

        for val in vals:
            val['royalty_tracking_line_detail_ids'] = [(0, 0, line) for line in val['royalty_tracking_line_detail_ids']]
        return vals
