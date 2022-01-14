from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _get_on_hand_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None,
                              strict=False, allow_negative=False):
        """ Return the on hand quantity
        :return: available quantity as a float
        """
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict)
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity'))
            if allow_negative:
                return available_quantity
            else:
                return available_quantity if float_compare(available_quantity, 0.0,
                                                           precision_rounding=rounding) >= 0.0 else 0.0
        else:
            availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
            for quant in quants:
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if
                            float_compare(available_quantity, 0, precision_rounding=rounding) > 0])
