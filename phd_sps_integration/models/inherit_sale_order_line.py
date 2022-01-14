from odoo import api, fields, models, _


class SalesOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ###################################
    # FIELDS
    ###################################
    sps_sequence_number = fields.Char('SPS Line Sequence', index=True)
    edi_transaction_line_ids = fields.One2many('edi.transaction.line', 'order_line_id')
    sps_ack_schedule_date = fields.Datetime(string="ACK Schedule Date", copy=False)

    ###################################
    # HELPER FUNCTIONS
    ###################################
    def _prepare_procurement_values(self, group_id=False):
        """
        Change schedule date of move line to SPS ACK schedule date if it was set
        """
        values = super(SalesOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        values['date_planned'] = self.sps_ack_schedule_date or values['date_planned']

        return values
