# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from odoo.addons.phd_royalty.models.royalty_tracking import CONFIRM
from odoo.exceptions import ValidationError
from datetime import datetime

PRODUCT_CONSUMABLE_TYPE = 'consu'


class MrpProductProduce(models.TransientModel):
    _inherit = 'mrp.product.produce'

    def _record_production(self):
        # Get workorder line group by product
        work_order_line_ids = self._workorder_line_ids().ids
        work_order_line_ids_by_product = self.env['mrp.product.produce.line'].read_group(
            domain=[('id', 'in', work_order_line_ids)], fields=['product_id', 'qty_done'], groupby='product_id')

        for line in work_order_line_ids_by_product:
            product_id = self.env['product.product'].browse(line['product_id'][0])
            if not product_id.type == PRODUCT_CONSUMABLE_TYPE:
                continue
            royalty_tracking_id = self.env['royalty.tracking'].search([('state', '=', CONFIRM),
                                                                       ('product_id', '=', product_id.id)],
                                                                      limit=1)
            if not royalty_tracking_id or not royalty_tracking_id.royalty_tracking_line_ids:
                continue
            last_tracking_line = royalty_tracking_id.royalty_tracking_line_ids[-1]
            current_tracking_info = last_tracking_line.royalty_info_id
            next_tracking_info_ids = royalty_tracking_id.royalty_info_ids.filtered(lambda info: info.min_qty
                                                                                                > current_tracking_info.min_qty)

            if next_tracking_info_ids:
                total_qty_consumed = sum(royalty_tracking_id.royalty_tracking_line_ids.mapped('qty_consumed'))
                next_line_info_id = next_tracking_info_ids[0]
                if (total_qty_consumed + line['qty_done']) >= next_line_info_id.min_qty:
                    qty_need_consume = next_line_info_id.min_qty - total_qty_consumed - 1
                    raise ValidationError(_(
                        "Need to consume %s first to close the current and change to next royalty tracking" % (
                            qty_need_consume)))

        res = super(MrpProductProduce, self)._record_production()
        return res

    def do_produce(self):
        """
        Validate producing quantity with royalty tracking
        :return: Produce action
        """

        # Update old done move
        has_produced_move = self.move_raw_ids.filtered(lambda move: move.state == 'done' and not move.has_produced)
        has_produced_move.write({
            'has_produced': True
        })

        res = super(MrpProductProduce, self).do_produce()

        # Get new produced move
        move_raw_ids = self.move_raw_ids.filtered(lambda move: move.state == 'done' and not move.has_produced)
        move_raw_ids.write({
            'has_produced': True
        })

        for move in move_raw_ids:
            if not move.product_id.type == PRODUCT_CONSUMABLE_TYPE:
                continue

            royalty_tracking_id = self.env['royalty.tracking'].search([('state', '=', CONFIRM),
                                                                       ('product_id', '=', move.product_id.id)],
                                                                      limit=1)

            if not royalty_tracking_id or not royalty_tracking_id.royalty_tracking_line_ids:
                continue

            last_tracking_line = royalty_tracking_id.royalty_tracking_line_ids[-1]
            current_tracking_info = last_tracking_line.royalty_info_id
            next_tracking_info_ids = royalty_tracking_id.royalty_info_ids.filtered(lambda info: info.min_qty
                                                                                                > current_tracking_info.min_qty)
            if next_tracking_info_ids:
                total_qty_consumed = sum(royalty_tracking_id.royalty_tracking_line_ids.mapped('qty_consumed'))
                next_line_info_id = next_tracking_info_ids[0]

                if (total_qty_consumed + move.quantity_done) == next_line_info_id.min_qty - 1:
                    move.product_id.write({
                        'standard_price': next_line_info_id.standard_price
                    })

                    last_tracking_line.write({
                        'date_end': move.date
                    })

                    self.env['royalty.tracking.line'].create({
                        'royalty_tracking_id': royalty_tracking_id.id,
                        'date_start': move.date,
                        'date_end': royalty_tracking_id.date_end,
                        'royalty_info_id': next_line_info_id.id
                    })
            production_id = move.raw_material_production_id
            self.env['royalty.tracking.line.detail'].create({
                'manufacture_date': move.date,
                'production_id': production_id.id,
                'lot_id': move.lot_id.id,
                'purchase_id': production_id.purchase_id.id,
                'partner_id': production_id.purchase_id.partner_id.id,
                'product_id': move.product_id.id,
                'finished_product_id': production_id.product_id.id,
                'product_uom_qty': move.quantity_done,
                'royalty_tracking_line_id': last_tracking_line.id
            })

        return res
