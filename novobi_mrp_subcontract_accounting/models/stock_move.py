# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _append_account_move_line(self, data_dict, partner_id, qty, amount,
                                  debit_account_id, credit_account_id, description):
        """
        Helper function to create debit/credit side
        """
        amount = float_round(amount, precision_digits=2)

        debit_mrp_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'debit': amount,
            'credit': 0,
            'account_id': debit_account_id,
        }

        credit_mrp_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'credit': amount,
            'debit': 0,
            'account_id': credit_account_id,
        }

        data_dict.update({"debit_{}".format(credit_account_id): debit_mrp_line_vals,
                          "credit_{}".format(credit_account_id): credit_mrp_line_vals})
        return data_dict

    def _calculate_extra_account_move_line(self, data_dict, partner_id, qty, debit_value, credit_value,
                                           debit_account_id, credit_account_id, description):
        """
        Can be overridden in different projects.
        """
        production_id = self.production_id

        # MO is finished
        if production_id and not self.scrap_ids and not self.scrapped:
            # MO's move for Final Product should have at most 1 dest_move, if generated from PO
            dest_moves = self.move_dest_ids
            if dest_moves and dest_moves[0].purchase_line_id:
                purchase_line = dest_moves[0].purchase_line_id
                product_cost = purchase_line.price_unit * qty
                interim_received_acc_id = self.product_id.categ_id.property_stock_account_input_categ_id

                """ MO Journal Entry
                OOTB
                Account                                     | Debit | Credit
                ---------------------------------------------------------------
                WIP                                         |       | Component Cost + PO Cost
                ---------------------------------------------------------------
                Stock Valuation                             | Component Cost + PO Cost  |
                ---------------------------------------------------------------
                
                We add these lines:
                ---------------------------------------------------------------
                WIP                                         | PO Cost |
                ---------------------------------------------------------------
                101130 Stock Interim Account (Received)     |         | PO Cost
                ---------------------------------------------------------------
                """
                if not float_is_zero(product_cost, precision_digits=2):
                    data_dict = self._append_account_move_line(data_dict, partner_id, qty, product_cost,
                                                               credit_account_id, interim_received_acc_id.id, description)
        return data_dict

    # Inherit
    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value,
                                       debit_account_id, credit_account_id, description):
        data_dict = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value,
                                                           debit_account_id, credit_account_id, description)

        # Add Lines to Journal Entry
        data_dict = self._calculate_extra_account_move_line(data_dict, partner_id, qty, debit_value, credit_value,
                                                            debit_account_id, credit_account_id, description)
        return data_dict

    def _prepare_common_svl_vals(self):
        vals = super()._prepare_common_svl_vals()
        if self.production_id and self.move_dest_ids and self.move_dest_ids[0].purchase_line_id:
            vals['stock_move_id'] = self.id
        else:
            if self.move_dest_ids and self.move_dest_ids[0].is_subcontract:
                vals['stock_move_id'] = self.move_dest_ids[0].id
        return vals
