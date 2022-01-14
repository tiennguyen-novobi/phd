from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    purchase_lead_time = fields.Integer(related='company_id.default_purchase_lead_time', readonly=False,
                                        required=True)
    assigning_z_score = fields.Float(related='company_id.default_assigning_z_score', readonly=False,
                                     required=True)
    order_analysis_interval = fields.Integer(related='company_id.default_order_analysis_interval',
                                             readonly=False, required=True)
    
    @api.constrains('purchase_lead_time')
    def _validate_purchase_lead_time(self):
        if self.purchase_lead_time < 0:
            raise UserError(_("Purchase Lead Time should be greater than or equal to 0"))
    
    @api.constrains('assigning_z_score')
    def _validate_assigning_z_score(self):
        if float_compare(self.assigning_z_score, 0, precision_digits=2) <= 0:
            raise UserError(_("Assigning Z-score should be greater than 0"))

    @api.constrains('order_analysis_interval')
    def _validate_order_analysis_interval(self):
        if self.order_analysis_interval <= 0:
            raise UserError(_("Order Analysis Interval should be greater than 0"))
