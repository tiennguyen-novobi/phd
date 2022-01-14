# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cc_tag = fields.Boolean(string='CC Tag', compute='_compute_is_cc_tag', store=True)
    is_credit_card_user = fields.Boolean(string='Credit Card User', compute='_compute_is_credit_card_user', store=True)

    @api.depends('category_id', 'category_id.is_cc_tag')
    def _compute_is_cc_tag(self):
        for partner in self:
            partner.is_cc_tag = False
            if any(partner.category_id.filtered(lambda category: category.is_cc_tag)):
                partner.is_cc_tag = True

    @api.depends('category_id', 'category_id.is_credit_card_user')
    def _compute_is_credit_card_user(self):
        for partner in self:
            partner.is_credit_card_user = False
            if any(partner.category_id.filtered(lambda category: category.is_credit_card_user)):
                partner.is_credit_card_user = True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('is_credit_card_charge', False):
            if self.env.context.get('is_credit_card_holder', False):
                args = expression.AND([[('is_credit_card_user', '=', True)], args])
            else:
                args = expression.AND([[('is_cc_tag', '=', True)], args])
        return self._name_search(name, args, operator, limit=limit)
