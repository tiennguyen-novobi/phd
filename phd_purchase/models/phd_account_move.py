import logging

from odoo import api, fields, models, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    stock_picking_ids = fields.Many2many('stock.picking', string='Receipts')

    def action_post(self):
        for invoice in self:
            for line_id in invoice.invoice_line_ids.filtered(lambda x: x.product_id):
                line_id.old_usa_description = line_id.usa_description if not line_id.is_change_usa_description else line_id.old_usa_description
                stock_picking_ids = invoice.stock_picking_ids.filtered(
                    lambda x: line_id.product_id.id in x.move_lines.mapped('product_id').ids)
                line_id._set_phd_description(stock_picking_ids)

        res = super(InheritAccountMove, self).action_post()
        return res


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    old_usa_description = fields.Text()
    is_change_usa_description = fields.Boolean()

    def _set_phd_description(self, picking_ids):
        self.ensure_one()
        if picking_ids:
            picking_name = ', '.join(picking_ids.mapped('name'))
            if self.purchase_line_id:
                order_name = self.purchase_line_id.order_id.name
                self.usa_description = '%s: %s %s' % (order_name, picking_name, self.product_id.name)
            else:
                self.usa_description = '%s, %s' % (picking_name, self.old_usa_description)
            self.is_change_usa_description = True
        else:
            self.usa_description = self.old_usa_description
