# Copyright © 2021 Novobi, LLC
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_acceptable_boms(self, warehouse, company):
        self.ensure_one()
        boms = self.bom_ids.filtered(lambda bom:
                                     (not bom.company_id or bom.company_id == company) and (
                                             bom.type == 'normal' or bom.type == "subcontract") and \
                                     (not bom.picking_type_id or bom.picking_type_id == warehouse.manu_type_id))
        return boms

    def get_manufacturing_order_data(self, warehouse, company):
        """
        Override all original method of me_replenishment_planing
        :param warehouse: the selected warehouse (be ingored)
        :param company: current company
        :return: as original.
        """
        bom_ids = mo_ids = []
        mo_dict = {}
        self._cr.execute(f"""
                    SELECT id, product_id, bom_id 
                    FROM mrp_production
                    WHERE state NOT IN ('draft', 'done', 'cancel')
                      AND company_id = {company.id}
                """)
        for line in self._cr.dictfetchall():
            mo_item = mo_dict.setdefault(line.get('id'), {})
            mo_item['produced_product_id'] = line.get('product_id')
            mo_item['bom_id'] = line.get('bom_id')
            mo_ids.append(line.get('id'))
            bom_ids.append(line.get('bom_id'))

        return mo_ids, bom_ids, mo_dict
    def get_rfq_qty_dict(self):
        return {}

    def get_active_receive_qty_dict(self):
        return {}

    def get_active_mrp_qty_dict(self):
        return {}
