# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    ###################################
    # ACTION
    ###################################
    has_produced = fields.Boolean("Field to check if move has produced")
