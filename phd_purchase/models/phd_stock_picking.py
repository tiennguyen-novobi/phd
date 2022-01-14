import logging
from odoo.osv import expression

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if self.env.context.get('phd_description', False):
            purchase_ID = self.env.context.get('purchase_id', False)
            if purchase_ID:
                args = expression.AND([[('purchase_id', '=', purchase_ID)], args])
        return self._name_search(name, args, operator, limit=limit)