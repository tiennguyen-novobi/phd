from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare

class PHDProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    lot_qty = fields.Float(store=True)

    # def name_get(self):
    #     return [(record.id, "%s - %s" % (record.name, record.lot_qty)) for record in self]
