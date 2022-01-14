# -*- coding: utf-8 -*-
##############################################################################
#
#    Open Source Management Solution
#    Copyright (C) 2015 to 2020 (<http://tiny.be>).
#
#    Copyright (C) 2016 Novobi LLC (<http://novobi.com>)
#
##############################################################################

from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil import tz


class MRPProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    default_date_time = fields.Datetime()

    @api.model
    def default_get(self, fields_list):
        res = super(MRPProductProduce, self).default_get(fields_list)
        context = self.env.context
        if context and 'default_date_time' in context:
            res.update({'default_date_time': context.get('default_date_time')})
        return res

