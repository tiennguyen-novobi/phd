from odoo import api, fields, models


class FilterLocationWizard(models.TransientModel):
    _name = 'filter.location'
    _description = 'Filter Location'

    location_id = fields.Many2one(
        'stock.location', string="Location", company_dependent=True, check_company=True,
        domain="[('usage', '=', 'internal'), ('is_visible', '=', 'true')]")
