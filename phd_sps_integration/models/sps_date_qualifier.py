# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SPSDateQualifier(models.Model):
    _name = 'sps.date.qualifier'
    _description = 'SPS Date Qualifier'

    name = fields.Char(
        'Name', required=True)
    code = fields.Char('Code', size=3, required=True)
