# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
from odoo import tools
import operator as op
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.models import expression

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ###################################
    # FIELDS
    ###################################
    qty_ordered = fields.Float(related="sale_line_ids.product_uom_qty")
    qty_backordered = fields.Float(string="Quantity Backordered", related="sale_line_ids.qty_backordered")
    default_code = fields.Char('Internal Reference', related="product_id.default_code")
    lot_name = fields.Char('Lot Name')
    is_credit_card_charges = fields.Boolean()
    credit_card_charges_payment_id = fields.Many2one('account.payment')

    ###################################
    # GENERAL FUNCTIONS
    ###################################

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        domain = []
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            domain = [(self._rec_name, operator, name)]
            if self._context.get('filter_another_field', False) and self._context.get('field_name', False):
                domain = ['|', (self._rec_name, operator, name),
                          (self._context.get('field_name', False), operator, name)]

        ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        recs = self.browse(ids)
        names = tools.lazy(lambda: dict(recs.recommend_bill_name_get()))
        return [(rid, tools.lazy(op.getitem, names, rid)) for rid in recs.ids]

    ###################################
    # COMPUTE FUNCTIONS
    ###################################
    def _compute_analytic_account(self):
        """
        If account move lines are imported from the file, the default analytic infos will overwrite the analytic accounts
        and tags even though those infos are defined in the files
        This function check if record has imported from file and only set the analytic default if file does not define
        those infos
        """
        is_rec_import_from_file = self._context.get('import_file')
        if is_rec_import_from_file:
            for record in self:
                rec = self.env['account.analytic.default'].account_get(
                    product_id=record.product_id.id,
                    partner_id=record.partner_id.commercial_partner_id.id or record.move_id.partner_id.commercial_partner_id.id,
                    account_id=record.account_id.id,
                    user_id=record.env.uid,
                    date=record.date_maturity,
                    company_id=record.move_id.company_id.id
                )
                if rec and not record.exclude_from_invoice_tab:
                    record.analytic_account_id = record.analytic_account_id or rec.analytic_id
                    record.analytic_tag_ids = record.analytic_tag_ids or rec.analytic_tag_ids
        else:
            super(AccountMoveLine, self)._compute_analytic_account()

    ###################################
    # HELPER FUNCTIONS
    ###################################

    def recommend_bill_name_get(self):
        res = []
        for record in self:
            bill_name = '%s Invoice Date: %s Due Date: %s' % (
                record.name_get()[0][1], record.date, record.date_maturity)
            res.append((record.id, bill_name))
        return res
