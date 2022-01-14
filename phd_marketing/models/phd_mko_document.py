# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PHDMkoDocument(models.Model):
    _name = 'phd.mko.document'
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }
    _order = "priority desc, id desc"

    ir_attachment_id = fields.Many2one('ir.attachment', string='Related attachment', required=True, ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority", help='Gives the sequence order when displaying a list of MRP documents.')

    def write(self, vals):
        doc = super(PHDMkoDocument, self).write(vals)
        return doc