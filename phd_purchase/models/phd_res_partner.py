import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PHDResPartner(models.Model):
    _inherit = 'res.partner'

    is_subcontractor = fields.Boolean('Subcontractor')