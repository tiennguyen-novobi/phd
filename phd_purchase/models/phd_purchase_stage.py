import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PHDSaleOrderStage(models.Model):
    _name = 'phd.purchase.order.stage'
    _order = "sequence"
    _fold_name = 'folded'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence')
    folded = fields.Boolean('Folded in kanban view',compute='_compute_stage_folded')

    def _compute_stage_folded(self):
        for stage in self:
            if (stage.name in ['RFQ Sent','To Approve','Closed', 'Cancelled']):
                if (self._context.get('subcontracting',False) and stage.name in ['Closed', 'Cancelled']):
                    stage.folded = False
                else:
                    stage.folded = True
            else:
                stage.folded = False