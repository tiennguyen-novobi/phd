import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PHDMrpOrderStage(models.Model):
    _name = 'phd.mrp.order.stage'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence')
    folded = fields.Boolean('Folded in kanban view')