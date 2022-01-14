# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    previous_version_template = fields.Many2one('product.template', string='Template Previous Version')
    latest_version_templates = fields.One2many('product.template', 'previous_version_template')

    @api.constrains('previous_version_template')
    def _check_version_recursion(self):
        if self.previous_version_template == self.id:
            raise ValidationError(_('Error ! You cannot set recursive products.'))
        return True

class ProductProduct(models.Model):
    _inherit = "product.product"

    previous_version = fields.Many2one('product.product', string='Previous Version')
    latest_versions = fields.One2many('product.product', 'previous_version')

    @api.constrains('previous_version')
    def _check_version_recursion(self):
        if self.previous_version == self.id:
            raise ValidationError(_('Error ! You cannot set recursive products.'))
        return True
