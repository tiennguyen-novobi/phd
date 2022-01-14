# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ExcelReportWizard(models.TransientModel):
    _name = 'excel.report.wizard'

    file_name = fields.Char("File Name")
    data = fields.Binary("Data")