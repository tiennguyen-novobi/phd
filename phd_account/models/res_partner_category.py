# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    is_cc_tag = fields.Boolean(string='CC Tag')
    is_credit_card_user = fields.Boolean(string='Credit Card User Tag')
