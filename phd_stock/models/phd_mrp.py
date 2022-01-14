import logging

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class PHDMrpOrder(models.Model):
    _inherit = 'mrp.production'

    vendor_wo = fields.Char(string='Vendor WO')

    purchase_id = fields.Many2one('purchase.order',
                                  string="Purchase Order",
                                  copy=False)