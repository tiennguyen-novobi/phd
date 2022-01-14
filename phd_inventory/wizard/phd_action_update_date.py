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


class PHDUpdateDate(models.TransientModel):
    _name = 'phd.update.date'

    res_id = fields.Integer()
    model = fields.Char()
    date_time = fields.Datetime(string='Date')
    is_update = fields.Boolean()
    field = fields.Char()
    action_name = fields.Char()
    update_action_name = fields.Char()

    def action_update_date(self):
        record_id = self.env[self.model].browse(self.res_id)
        if self.is_update:
            if record_id and self.field and self.field in record_id and hasattr(record_id, self.update_action_name):
                getattr(record_id, self.update_action_name)(self.date_time, self.field)
        else:
            res = record_id.with_context(default_date_time=self.date_time).__getattribute__(self.action_name)()
            if res:
                context = self.env.context.copy()
                context.update({'default_date_time': self.date_time})
                res.update({'context': context})
                return res
