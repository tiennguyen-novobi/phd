# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ###############################
    # FIELDS DECLARATION
    ###############################
    po_perc = fields.Float(related='company_id.po_perc', required=True, readonly=False)
    replenishment_default_warehouse = fields.Many2one('stock.warehouse', related='company_id.default_warehouse', required=True, readonly=False)
