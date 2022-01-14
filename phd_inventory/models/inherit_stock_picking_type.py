from odoo import api, fields, models, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    default_dest_address_id = fields.Many2one('res.partner', string="Default Destination Address", check_company=True)
