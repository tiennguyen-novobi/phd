# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ###############################
    # FIELDS DECLARATION
    ###############################
    po_perc = fields.Float(
        _('Ordered Quantity from PO (%)'),
        compute='_compute_po_perc', inverse='_inverse_po_perc',
        digits=dp.get_precision('Adjust Percentage'))

    ###############################
    # COMPUTED FUNCTIONS
    ###############################
    @api.depends('product_variant_ids.po_perc')
    def _compute_po_perc(self):
        self.barcode = False
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.po_perc = template.product_variant_ids.po_perc
            # When creating new template, template.product_variant_ids = 0
            else:
                template.po_perc = False

    def _inverse_po_perc(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.po_perc = self.po_perc

    ###############################
    # ACTION METHODS
    ###############################
    def action_open_replenishment_planning_for_template(self):
        self.ensure_one()
        action = self.product_variant_id.action_open_replenishment_planning_for_product()
        return action
