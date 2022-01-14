from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = "res.company"
    
    default_purchase_lead_time = fields.Integer(string='Purchase Lead Time', default=30)
    default_assigning_z_score = fields.Float(string='Assigning Z-score', default=1.13)
    default_order_analysis_interval = fields.Integer(string='Order Analysis Interval', default=6)
