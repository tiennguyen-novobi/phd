from odoo import api, fields, models, _


BOM_TYPE_SUBCONTRACT = 'subcontract'
CONSUMPTION_TYPE_FLEXIBLE = 'flexible'


class PHDMrpBom(models.Model):
    _inherit = 'mrp.bom'

    ###################################
    # FIELDS
    ###################################
    type = fields.Selection(default=BOM_TYPE_SUBCONTRACT)
    consumption = fields.Selection(default=CONSUMPTION_TYPE_FLEXIBLE)

    ###################################
    # CONSTRAINS
    ###################################

    @api.constrains('subcontractor_ids')
    def _set_subcontractor(self):
        for record in self:
            record.subcontractor_ids.write({'is_subcontractor': True})
