# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_compare, float_round


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def get_vendor_for_replenishment_planning(self, product, line_data):
        partner = None
        if 'vendor_id' in line_data:
            partner = self.env['res.partner'].browse(line_data['vendor_id'])
        else:
            po_qty = float(line_data.get('po_qty', 0))
            existed_supplier = product.with_company(self.env.company.id)._select_seller(quantity=po_qty)
            if existed_supplier:
                partner = existed_supplier[0].name
        return partner

    def create_purchase_order_from_replenishment_planning(self, data, warehouse_id):
        # Remove 0 request quantity line
        decimal_pre = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        product_env = self.env['product.product']
        po_lines_group_by_vendor = {}
        po_dict = {}
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        new_purchase_orders = self.browse()
        for line in data:
            product = product_env.browse(int(line['product_id']))
            po_qty = float(line['po_qty'])
            if product and float_compare(po_qty, 0.0, precision_digits=decimal_pre) > 0:
                vendor = self.get_vendor_for_replenishment_planning(product, line)
                if not vendor:
                    raise UserError(_("There is no matching vendor to generate the purchase order for product %s. "
                                      "Go on the product form and complete the list of vendors.") % (product.display_name))
                if po_lines_group_by_vendor.get(vendor.id, False):
                    po_lines_group_by_vendor[vendor.id].append({
                        'product_id': product.id,
                        'date_planned': fields.Datetime.now(),
                        'product_qty': po_qty,
                        'price_unit': product.standard_price,
                        'order_id': po_dict[vendor.id],
                        'name': product.display_name,
                        'product_uom': product.uom_id.id
                    })
                else:
                    po = self.create({
                        'state': 'draft',
                        'date_order': fields.Datetime.now(),
                        'partner_id': vendor.id,
                        'picking_type_id': warehouse.in_type_id.id,
                        'order_line': []
                    })
                    new_purchase_orders |= po
                    po_dict[vendor.id] = po.id
                    po_lines_group_by_vendor[vendor.id] = [{
                        'product_id': product.id,
                        'date_planned': fields.Datetime.now(),
                        'product_qty': po_qty,
                        'price_unit': product.standard_price,
                        'order_id': po_dict[vendor.id],
                        'name': product.display_name,
                        'product_uom': product.uom_id.id
                    }]

        if new_purchase_orders:
            po_line_env = self.env["purchase.order.line"]
            for key, lines in po_lines_group_by_vendor.items():
                po_line_env.create(lines)

        return new_purchase_orders
