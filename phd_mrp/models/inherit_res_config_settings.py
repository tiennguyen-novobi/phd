# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_reserve_subcontracting_mo = fields.Boolean("Automatically Check Availability for Subcontracting MO",
                                                    config_parameter='phd_mrp.auto_reserve_subcontracting_mo')