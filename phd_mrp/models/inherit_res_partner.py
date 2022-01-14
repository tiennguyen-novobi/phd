# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ###################################
    # FIELDS
    ###################################
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Receipt Operation Type',
        help=_("The Receipt Operation Type to define receipt source and destination location"))

    subcontract_picking_type_id = fields.Many2one(
        'stock.picking.type', 'Subcontracting Operation Type',
        help=_("The Subcontract Operation Type to define component location and finished product location"))
