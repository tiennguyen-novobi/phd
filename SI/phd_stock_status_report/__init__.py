# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api
from . import models

def _init_inventory_status_report_line(cr, registry):
    """Remove all existing personal LinkedIn accounts"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['product.product'].search([('forecasted_demand_ok', '=', True)]).insert_product_into_stock_status_tracking(True)
