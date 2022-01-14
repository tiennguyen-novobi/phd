# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ###################################
    # FIELDS
    ###################################

    month_of_shelf_life_require = fields.Integer('Partner Shelf-life requirement for Transfer')

    check_previous_shipment_date = fields.Boolean('Check Previous Shipment date')

    @api.constrains('month_of_shelf_life_require')
    def _check_month_of_shelf_life_require(self):
        for record in self:
            if record.month_of_shelf_life_require < 0:
                raise ValidationError(_('Number of required Shell life month require must be greater or equal to 0.'))
