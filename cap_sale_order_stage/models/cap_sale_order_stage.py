# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

from odoo import fields, models, api

class CapSaleOrderStage(models.Model):
    """Manage 'sale.order.stage' model."""
    _name = "sale.order.stage"
    _order = "sequence asc"

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Name", required=True)
    datetime_field_name = fields.Char(string="Datetime Field Name")

