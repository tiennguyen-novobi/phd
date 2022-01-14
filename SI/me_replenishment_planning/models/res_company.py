# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class ResCompany(models.Model):
    _inherit = 'res.company'

    ###############################
    # FIELDS DECLARATION
    ###############################
    po_perc = fields.Float('Replenishment Percentage', digits=dp.get_precision('Adjust Percentage'), default=100)
    default_warehouse = fields.Many2one('stock.warehouse', string='Warehouse')
