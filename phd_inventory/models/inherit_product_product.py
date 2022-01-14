# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ###################################
    # FIELDS
    ###################################
    description_1 = fields.Text('Description 1')
    description_2 = fields.Text('Description 2')

    case_upc = fields.Char(string='Case UPC')

    unit_per_case = fields.Integer(string='Units Per Case')
    unit_per_pallet = fields.Integer(string='Units Per Pallet')

    case_per_pallet = fields.Integer(string='Cases Per Pallet')
    case_per_layer = fields.Integer(string='Cases Per Layer')
    number_of_layers = fields.Integer(string='Number of Layers')

    case_length = fields.Float(string='Case Length',  digits=(16, 3))
    case_width = fields.Float(string='Case Width',  digits=(16, 3))
    case_height = fields.Float(string='Case Height',  digits=(16, 3))
