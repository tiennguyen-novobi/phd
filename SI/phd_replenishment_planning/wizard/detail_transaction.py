# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class DetailTransaction(models.TransientModel):
    _inherit = "detail.transaction"

    date_to_complete = fields.Datetime('Scheduled Date')
