# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.phd_sps_integration.models.edi_transaction import CHANGE_REJECT

class RejectEDI860(models.TransientModel):
    _name = 'reject.edi.860'
    _description = 'Popup to fill Note before reject the EDI 860'

    edi_transaction_id = fields.Many2one('edi.transaction')
    note = fields.Text()

    def action_confirm(self):
        self.ensure_one()
        edi_transaction_id = self.edi_transaction_id
        edi_transaction_id.write({'state': CHANGE_REJECT,
                                  'note': self.note})
        edi_transaction_id.action_submit_edi_865()
        return True
