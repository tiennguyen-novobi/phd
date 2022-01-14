# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class RawMaterialConsumptionReport(models.Model):
    _name = "raw.material.consumption.report"
    _description = "Raw Material Consumption Report"
    _auto = False
    _rec_name = 'date_approve'
    _order = 'date_approve desc'

    ###################################
    # FIELDS
    ###################################
    name = fields.Char("Mo Name", readonly=True)
    date_approve = fields.Datetime('Confirmation Date', readonly=True)
    purchase_id = fields.Many2one('purchase.order', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)

    qty_ordered = fields.Float(readonly=True)
    qty_received = fields.Float(readonly=True)
    variance = fields.Float(readonly=True)

    qty_label_usage = fields.Float(readonly=True)
    label_variance = fields.Float(readonly=True)
    label_usage_rate = fields.Float(readonly=True, store=True)

    creatine_base_qty = fields.Float(readonly=True)
    qty_creatine_usage = fields.Float(readonly=True)
    creatine_variance = fields.Float(readonly=True, store=True)
    creatine_usage_rate = fields.Float(readonly=True, store=True)

    default_code = fields.Char(readonly=True)

    ###################################
    # INIT FUNCTIONS
    ###################################
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
             CREATE OR REPLACE VIEW %s AS (
                 %s %s %s %s %s
             )
         ''' % (
            self._table, self._with(), self._select(), self._from(), self._where(), self._group_by()
        ))

    ###################################
    # HELPER FUNCTIONS
    ###################################
    @api.model
    def _with(self):
        with_str = """
            WITH sub_table AS (
                        SELECT move.raw_material_production_id AS id,
                        sum(CASE WHEN product_move.is_product_label = TRUE then move.product_uom_qty
                                            ELSE 0 END) AS qty_label_usage,
                        sum(CASE WHEN product_move.is_creatine = TRUE then move.product_uom_qty
                                            ELSE 0 END) AS qty_creatine_usage,
                        po.id as purchase_id,
                        po.date_approve,
                        po.partner_id,
                        product.id AS product_id,
                        product.default_code AS default_code,
                        pol.product_qty / line_uom.factor * product_uom.factor as qty_ordered,
                        pol.qty_received / line_uom.factor * product_uom.factor as qty_received,
                        mp.bom_id,
                        mp.name,
                        mp.state
                FROM mrp_production mp
                                JOIN purchase_order_line pol ON pol.id = mp.purchase_line_id
                                JOIN purchase_order po ON mp.purchase_id = po.id
                                JOIN stock_move move ON move.raw_material_production_id = mp.id
                                JOIN product_product product ON mp.product_id = product.id
                                JOIN product_template ON product.product_tmpl_id = product_template.id
                                LEFT JOIN uom_uom line_uom ON line_uom.id = pol.product_uom
                                LEFT JOIN uom_uom product_uom ON product_uom.id = product_template.uom_id
                                JOIN product_product product_move ON move.product_id = product_move.id
                WHERE mp.purchase_id IS NOT NULL
                GROUP BY move.raw_material_production_id, po.id, mp.id, product.id, pol.product_qty, line_uom.factor,
                         product_uom.factor, pol.qty_received)
        """
        return with_str

    @api.model
    def _select(self):
        select_str = """
            SELECT
               sub_table.purchase_id,
               sub_table.name,
               sub_table.date_approve,
               sub_table.id,
               sub_table.partner_id,
               sub_table.product_id,
               sub_table.default_code,
               qty_ordered,
               qty_received,
               (qty_ordered - qty_received) as variance,
               qty_label_usage,
               (qty_label_usage - qty_received) as label_variance,
               (qty_label_usage - qty_received) / NULLIF(qty_label_usage, 0) as label_usage_rate,
               sum(case when product_bom.is_creatine = TRUE
                    then (mrp_bom_line.product_qty / line_uom.factor * product_uom.factor) else 0 end)* qty_ordered
                    AS creatine_base_qty,
               qty_creatine_usage,
               (qty_creatine_usage
               - sum(case when product_bom.is_creatine = TRUE
                    then (mrp_bom_line.product_qty / line_uom.factor * product_uom.factor) else 0 end)* qty_ordered)
                                                                                                AS creatine_variance,
               (qty_creatine_usage - sum(case when product_bom.is_creatine = TRUE
                                        then (mrp_bom_line.product_qty / line_uom.factor * product_uom.factor)
                                        else 0 end)* qty_ordered ) / NULLIF(qty_creatine_usage, 0)
                                        AS creatine_usage_rate
        """
        return select_str

    @api.model
    def _from(self):
        return """
             FROM sub_table
                LEFT JOIN mrp_bom on bom_id = mrp_bom.id
                LEFT JOIN mrp_bom_line on  mrp_bom.id = mrp_bom_line.bom_id
                LEFT JOIN product_product product_bom on mrp_bom_line.product_id = product_bom.id
                JOIN product_template ON product_bom.product_tmpl_id = product_template.id
                LEFT JOIN uom_uom line_uom ON line_uom.id = mrp_bom_line.product_uom_id
                LEFT JOIN uom_uom product_uom ON product_uom.id = product_template.uom_id
        """

    @api.model
    def _where(self):
        return """
                    WHERE state IN ('progress', 'done')
                """

    @api.model
    def _group_by(self):
        return """
                    GROUP BY sub_table.id, sub_table.purchase_id, sub_table.date_approve, sub_table.partner_id,
                            sub_table.product_id, sub_table.default_code, sub_table.name,
                            qty_ordered, qty_received, qty_label_usage, qty_creatine_usage
            """
