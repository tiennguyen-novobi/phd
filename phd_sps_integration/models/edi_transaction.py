# -*- coding: utf-8 -*-
import dicttoxml
import base64
import xmltodict

from odoo import models, fields, api, _
from datetime import datetime
from xml.dom.minidom import parseString
from collections import Counter
from odoo.exceptions import Warning, ValidationError
from odoo.osv import expression
from ..utils.exceptions import EDITransactionValidationError
from ..utils.helpers import ensure_list

# Tag name using for parsing EDI Document XML files
ORDER_TAG = 'Order'
ORDER_CHANGE_TAG = 'OrderChange'

HEADER_TAG = 'Header'

ORDER_HEADER_PATH = 'OrderHeader'
SPS_TRADING_PARTNER_ID_PATH = 'TradingPartnerId'
CLIENT_ORDER_REF = 'PurchaseOrderNumber'
DIVISION = 'Division'
SO_ORDER_DATE_PATH = 'PurchaseOrderDate'
VENDOR_CODE_PATH = 'Vendor'
PO_CHANGE_DATE = 'POChangeDate'
CUSTOMER_ORDER_NUMBER = 'CustomerOrderNumber'

PAYMENT_TERM_PATH = 'PaymentTerms'
TERM_DESCRIPTION_PATH = 'TermsDescription'
INCOTERM_PATH = 'FOBRelatedInstruction'
INCOTERM_CODE_PATH = 'FOBPayCode'

DATE_LIST_PATH = 'Dates'
DATE_QUALIFIER_PATH = 'DateTimeQualifier'
DATE_PATH = 'Date'
LATEST_DELIVERY_DATE_CODE = '063'
EARLIEST_DELIVERY_DATE_CODE = '064'

ADDRESS_PATH = 'Address'
ADDRESS_TYPE_CODE_PATH = 'AddressTypeCode'
ADDRESS_LOCATION_NUMBER_PATH = 'AddressLocationNumber'
ADDRESS_NAME_PATH = 'AddressName'

PACKAGING_PATH = 'Packaging'
PACKAGING_CHARACTER_PATH = 'PackagingCharacteristicCode'
PACKAGING_DESCRIPTION_PATH = 'PackagingDescription'

CARRIER_ROUTING_INFO_PATH = 'CarrierInformation'
CARRIER_ROUTING_PATH = 'CarrierRouting'

ADDRESS_TYPE_SHIP_TO = 'ST'
ADDRESS_TYPE_BUYING_PARTY = 'BY'
ADDRESS_TYPE_BILL_TO_PARTY = 'BT'

LINE_ITEM_TAG = 'LineItem'
ORDER_LINE_TAG = 'OrderLine'
DEFAULT_CODE_TAG = 'VendorPartNumber'
CUSTOMER_PRODUCT_CODE_TAG = 'BuyerPartNumber'
PRODUCT_UOM_QTY_TAG = 'OrderQty'
PRICE_UNIT_TAG = 'PurchasePrice'
LINE_SEQUENCE_NUMBER_TAG = 'LineSequenceNumber'
LINE_CHANGE_STATUS_CODE_TAG = 'LineChangeCode'

# EDI Document type
PO = '850'
PO_ACK = '855'
PO_CHANGE = '860'
PO_CHANGE_ACK = '865'

# Type of EDI 855 (Acknowledgement)
ACK_CHANGE = 'AC'
ACK_NO_CHANGE = 'AD'
REJECT = 'RD'

# Type of EDI 865 (Change Acknowledgement)
CHANGE_ACK_NO_CHANGE = 'AK'
CHANGE_ACK_REJECT = 'RJ'

ACK = 'draft'
ACK_SENT = 'ack_sent'
APPROVE = 'approve'
CHANGE_REJECT = 'reject'

PO_PREFIX = 'PO'
PO_ACK_PREFIX = 'PR'
PO_CHANGE_PREFIX = 'PC'
PO_CHANGE_ACK_PREFIX = 'CA'

# Using for Order Acknowledgement EDI 855
LINE_ACCEPT = 'IA'
LINE_DATE_RESCHEDULED = 'DR'
LINE_QUANTITY_CHANGE = 'IQ'
LINE_REJECT = 'IR'
LINE_CHANGE_PRICING = 'IP'
LINE_BACK_ORDER = 'IB'

# Using for Order Change EDI 860
LINE_CHANGE = 'CA'
LINE_DELETE = 'DI'
LINE_QTY_DECREASE = 'QD'
LINE_QTY_INCREASE = 'QI'
LINE_DATE_CHANGE = 'CT'
LINE_PRICE_QTY_CHANGE = 'PQ'
LINE_PRICE_CHANGE = 'PC'
LINE_ADD = 'AI'


class EDITransaction(models.Model):
    _name = "edi.transaction"
    _description = "EDI Transaction"

    ###################################
    # FIELDS
    ###################################
    order_id = fields.Many2one('sale.order', ondelete='cascade', string='Origin', required=True)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner')

    has_rejected_reason = fields.Boolean(related="partner_id.has_sps_rejected_reason")

    type = fields.Selection([(PO_ACK, _('PO Acknowledgement')), (PO_CHANGE, _('PO Change'))],
                            string='Document Type', default=PO_ACK, required=True)
    ack_type = fields.Selection(selection=[(ACK_CHANGE, _('Acknowledge - With Detail and Change')),
                                           (ACK_NO_CHANGE, _('Acknowledge - With Detail No Change')),
                                           (REJECT, _('Rejected - With Detail'))],
                                string='Acknowledgement type')
    state = fields.Selection(
        [(ACK, _('Draft')), (ACK_SENT, _('ACK Sent')), (APPROVE, _('Approve')), (CHANGE_REJECT, _('Reject'))],
        string='State', default=ACK)

    order_change_state = fields.Selection(related="state")

    transaction_date = fields.Date(string='Transaction Date', required=True, default=lambda self: datetime.now().date())

    ship_date = fields.Datetime(string='Ship Date')

    order_line_ids = fields.One2many(related='order_id.order_line')
    edi_transaction_line_ids = fields.One2many('edi.transaction.line', 'edi_transaction_id')
    attachment_id = fields.Many2one('ir.attachment', string='EDI 855 XML', copy=False)
    note = fields.Char(string="Note")

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    @api.model
    def create(self, values):
        res = super(EDITransaction, self).create(values)

        order_id = res.order_id
        if order_id and res.type == PO_CHANGE:
            message = _(
                'The Quotation has the Order Change (EDI 860) <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a> '
                '(Change date is %s) need to be processed<br><br> '
                'You should process the Order Change before confirming the Quotation.') % (
                          res._name, res.id, res.display_name, res.transaction_date)
            order_id.activity_schedule('mail.mail_activity_data_todo', note=message,
                                       summary="Order Change (EDI 860)")

        return res

    ###################################
    # CONSTRAINTS FUNCTIONS
    ###################################
    @api.constrains('edi_transaction_line_ids')
    def _check_order_ack_line_status_code(self):
        if self.type == PO_ACK:
            ack_status_codes_by_order_line_id = self.edi_transaction_line_ids.mapped(
                lambda ack_line: (ack_line.order_line_id, ack_line.ack_status_code))

            # Get number of ack line for each Order line
            ack_line_count_by_order_line = Counter(list(map(lambda rec: rec[0], ack_status_codes_by_order_line_id)))

            # Get number of each status code for each Order line
            ack_line_status_code_count = Counter(ack_status_codes_by_order_line_id)

            validation_error_messeage = []
            for order_line, num_of_ack in ack_line_count_by_order_line.items():
                if num_of_ack > 1:
                    order_line_product_name = order_line.product_id.display_name
                    if ack_line_status_code_count.get((order_line, LINE_ACCEPT)):
                        validation_error_messeage.append(
                            _("%s has Accepted Line already, please remove other lines.") % order_line_product_name)
                    elif ack_line_status_code_count.get((order_line, LINE_REJECT)):
                        validation_error_messeage.append(
                            _("%s has Rejected Line already, please remove other lines.") % order_line_product_name)
                    elif ack_line_status_code_count.get((order_line, LINE_QUANTITY_CHANGE), 0) > 1:
                        validation_error_messeage.append(_(
                            "%s has Quantity Changed Line already, please remove other Quantity change lines.") % order_line_product_name)
                    elif ack_line_status_code_count.get((order_line, LINE_DATE_RESCHEDULED), 0) > 1:
                        validation_error_messeage.append(_(
                            "%s has Date Rescheduled Line already, please remove other Date Rescheduled lines.") % order_line_product_name)
            if validation_error_messeage:
                raise ValidationError('\n- '.join(validation_error_messeage))

    ###################################
    # GENERAL FUNCTIONS
    ###################################
    def name_get(self):
        res = []
        for ack in self:
            name = (ack.type == PO_ACK and PO_ACK_PREFIX) or (ack.type == PO_CHANGE and PO_CHANGE_PREFIX)
            name += ack.order_id.name
            res.append((ack.id, name))
        return res

    ###################################
    # SCHEDULED ACTION
    ###################################
    def action_import_sps_850(self):
        res = self.action_import_edi_transaction(PO)
        return res

    def action_import_edi_860(self):
        res = self.action_import_edi_transaction(PO_CHANGE)
        return res

    ###################################
    # PUBLIC FUNCTIONS
    ###################################
    def action_import_edi_transaction(self, doc_type):
        """
        Sync EDI transaction from SPS to Odoo Database
        :param doc_type: type of document (850,855,etc.)
        :type doc_type: str
        :return:
        :rtype:
        """
        edi_files = self.env['phd.sps.commerce.file'].search([('sync_status', 'not in', ['done', 'error']),
                                                              ('document_type', '=', doc_type)])
        has_sync_succeeded = True
        date_now = datetime.now()
        for edi_file in edi_files:
            edi_xml = edi_file.attachment_id.datas.decode('utf-8')
            edi_xml = base64.b64decode(edi_xml)

            # Parse EDI transaction from xml to dict
            edi_dict = xmltodict.parse(edi_xml)

            try:
                # Get vals and model need to sync with Odoo
                vals, sync_model = self.get_vals_from_edi(edi_dict, doc_type)
                if vals and sync_model:
                    sync_rec_id = self.env[sync_model].create(vals)

                    edi_file.update({
                        'sync_status': 'done',
                        'last_imported': date_now,
                        'origin': "%s,%s" % (sync_rec_id._name, sync_rec_id.id)
                    })
            except EDITransactionValidationError as e:
                has_sync_succeeded = False
                edi_file.write({'sync_status': 'error'})
                if edi_file and edi_file.sync_status in 'error':
                    # Send notify to EDI Files chatter and send email
                    edi_file_url = edi_file.get_sps_file_url()
                    body = _(e.name.replace('\n', '<br>')) + \
                           '<br><br><a style="font-weight:bold" href="%s">View in Odoo</a>' % edi_file_url

                    edi_file.with_context(mail_notify_force_send=True).message_post(body=body,
                                                                                    subject='Error when import EDI %s %s'
                                                                                            % (doc_type,
                                                                                               edi_file.display_name),
                                                                                    message_type='email',
                                                                                    subtype='mt_comment')
        return has_sync_succeeded

    def action_approve_ack(self):
        for ack in self:
            if ack.ack_type == ACK_CHANGE:
                for ack_line in ack.edi_transaction_line_ids:
                    ack_status_code = ack_line.ack_status_code
                    if ack_status_code == LINE_REJECT:
                        ack_line.order_line_id.unlink()
                    elif ack_status_code == LINE_QUANTITY_CHANGE:
                        ack_line.write({'old_product_uom_qty': ack_line.order_line_id.product_uom_qty})
                        ack_line.order_line_id.write({'product_uom_qty': ack_line.product_uom_qty})
                    elif ack_status_code == LINE_DATE_RESCHEDULED:
                        ack_line.order_line_id.write({'sps_ack_schedule_date': ack_line.product_schedule_date})
                if ack.ship_date:
                    ack.order_id.write({'commitment_date': ack.ship_date})
            ack.write({'state': APPROVE})

    def action_approve_change(self):
        for ack in self:
            for ack_line in ack.edi_transaction_line_ids:
                change_status_code = ack_line.change_status_code

                if change_status_code == LINE_CHANGE:
                    ack_line.order_line_id.write({
                        'product_uom_qty': ack_line.product_uom_qty,
                        'sps_ack_schedule_date': ack_line.product_schedule_date,
                        'price_unit': ack_line.price_unit
                    })
                elif ack_line.change_status_code == LINE_DELETE:
                    ack_line.order_line_id.unlink()
                elif ack_line.change_status_code == LINE_ADD:
                    ack.order_id.write({'order_line': [(0, 0, {
                        'edi_transaction_line_ids': [(4, ack_line.id, 0)],
                        'sps_sequence_number': ack_line.sps_sequence_number,
                        'product_id': ack_line.product_id.id,
                        'product_uom_qty': ack_line.product_uom_qty,
                        'price_unit': ack_line.price_unit
                    })]})
                elif change_status_code in [LINE_QTY_DECREASE, LINE_QTY_INCREASE]:
                    ack_line.order_line_id.write({'product_uom_qty': ack_line.product_uom_qty})
                elif change_status_code == LINE_DATE_CHANGE:
                    ack_line.order_line_id.write({'sps_ack_schedule_date': ack_line.product_schedule_date})
                elif change_status_code == LINE_PRICE_CHANGE:
                    ack_line.order_line_id.write({
                        'price_unit': ack_line.price_unit
                    })
                elif change_status_code == LINE_PRICE_QTY_CHANGE:
                    ack_line.order_line_id.write({
                        'product_uom_qty': ack_line.product_uom_qty,
                        'price_unit': ack_line.price_unit
                    })
            ack.write({'state': APPROVE})
            ack.action_submit_edi_865()

    def action_reject_change(self):
        self.ensure_one()
        view = self.env.ref('phd_sps_integration.view_reject_edi_860_popup')
        return {
            'string': 'Fill Note for reason of refusal',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'reject.edi.860',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_edi_transaction_id': self.id
            },
        }

    def action_submit_edi_865(self):
        for edi in self:
            if not edi.order_id.partner_id.has_sps_order_change_ack:
                continue
            edi_865_xml = edi.create_edi_865_xml()
            if edi_865_xml:
                filename = PO_CHANGE_ACK_PREFIX + edi.order_id.name + '.xml'
                filename = filename.replace('/', '_')
                fd = {
                    'name': filename,
                    'data': edi_865_xml,
                    'doc_type': PO_CHANGE_ACK,
                    'vals': {
                        'origin': "%s,%s" % (edi._name, edi.id)
                    }
                }
                sps_file_processor = self.env['phd.sps.commerce.file']
                sps_file_processor.create_edi_file_send_to_sps(fd)

    def action_submit_edi_855(self):
        date_now = datetime.now().date()
        for edi in self:
            edi.write({
                'state': ACK_SENT,
                'transaction_date': date_now
            })
            edi._update_new_price_to_order_edi_855()
            edi_855_xml = edi.create_edi_855_xml()
            if edi_855_xml:
                filename = PO_ACK_PREFIX + edi.order_id.name + '.xml'
                filename = filename.replace('/', '_')
                fd = {
                    'name': filename,
                    'data': edi_855_xml,
                    'doc_type': PO_ACK,
                    'vals': {
                        'origin': "%s,%s" % (edi._name, edi.id)
                    }
                }
                sps_file_processor = self.env['phd.sps.commerce.file']
                edi.attachment_id = sps_file_processor.create_edi_file_send_to_sps(fd).attachment_id

    ###################################
    # EDI 855 HELPER FUNCTIONS
    ###################################
    def _update_new_price_to_order_edi_855(self):
        if self.ack_type == ACK_CHANGE:
            for line in self.edi_transaction_line_ids.filtered(
                    lambda line: line.ack_status_code == LINE_CHANGE_PRICING):
                line.order_line_id.price_unit = line.price_unit

    def create_edi_855_xml(self):
        meta_dict = {'Meta': {'Version': '1.0'}}
        header_dict = self._prepare_855_edi_header()
        line_items = self._prepare_855_edi_ack_lines()

        edi_855_dict = {'OrderAck': [meta_dict, header_dict] + line_items}

        # Convert dictionary to xml
        xml = dicttoxml.dicttoxml(edi_855_dict, attr_type=False, root=False)
        xml = xml.decode("utf-8")
        xml = xml.replace('<item>', '').replace('</item>', '')
        xml = parseString(xml).toprettyxml()
        return xml

    def _prepare_855_edi_header(self):
        order_id = self.order_id
        ack_type = ACK_CHANGE if self.ack_type == REJECT else self.ack_type
        order_header_dict = {'OrderHeader': {
            'TradingPartnerId': order_id.sps_trading_partner_id,
            'PurchaseOrderNumber': order_id.client_order_ref,
            'TsetPurposeCode': '00',
            'PurchaseOrderDate': order_id.date_order.date(),
            'AcknowledgementType': ack_type,
            'AcknowledgementDate': self.transaction_date,
            'Vendor': order_id.vendor_code or ''
        }}
        partner_id = order_id.partner_shipping_id or order_id.partner_id

        address_dict = {'Address': {
            'AddressTypeCode': ADDRESS_TYPE_SHIP_TO,
            'AddressLocationNumber': partner_id.address_location_number,
            'AddressName': partner_id.name or '',
            'Address1': partner_id.street or '',
            'Address2': partner_id.street2 or '',
            'City': partner_id.city or '',
            'State': partner_id.state_id.code or '',
            'PostalCode': partner_id.zip or '',
            'Country': partner_id.country_id.code or '',
        }}

        dates_dict = {'Dates': {
            'DateTimeQualifier': self.partner_id.sps_current_scheduled_delivery_date_code if self.partner_id.sps_current_scheduled_delivery_date_code else self.partner_id.sps_requested_delivery_date_code.code,
            'Date': self.ship_date.date(),
        }} if self.ship_date else {}

        header_dict = {'Header': dict(**order_header_dict, **dates_dict, **address_dict)}
        return header_dict

    def _prepare_855_edi_ack_lines(self):
        order_line_ids = self.order_line_ids

        line_items = []
        ack_type = self.ack_type
        default_status_code = LINE_ACCEPT if (ack_type == ACK_CHANGE or ack_type == ACK_NO_CHANGE) else LINE_REJECT
        for line in order_line_ids:
            acknowledgment_lines = []

            product_alias_name = line.product_id.buyer_ids.filtered(
                lambda info: info.partner_id == self.partner_id)
            product_alias_name = product_alias_name and product_alias_name[0].product_name

            order_line_dict = {'OrderLine': {
                'LineSequenceNumber': line.sps_sequence_number or '',
                'BuyerPartNumber': product_alias_name or '',
                'VendorPartNumber': line.product_id.default_code,
                'EAN': line.product_id.barcode or '',
                'OrderQty': line.product_uom_qty,
                'OrderQtyUOM': 'EA',
                'PurchasePrice': line.price_unit,
                'PurchasePriceBasis': 'PE'
            }, 'ProductOrItemDescription': {
                'ProductCharacteristicCode': '08',
                'ProductDescription': line.name,
            }}
            edi_transaction_line_ids = line.edi_transaction_line_ids.filtered(
                lambda ack_line: ack_line.edi_transaction_id.id == self.id)
            if not edi_transaction_line_ids:
                acknowledgment_line_dict = {'LineItemAcknowledgement': {
                    'ItemStatusCode': default_status_code,
                    'ItemScheduleQty': line.product_uom_qty,
                    'ItemScheduleUOM': 'EA',
                    'ItemScheduleQualifier': line.order_id.partner_id.sps_item_schedule_qualifier or '068',
                    'ItemScheduleDate': (line.scheduled_date and line.scheduled_date.date()) or ''
                }}
                acknowledgment_lines.append(acknowledgment_line_dict)
            else:
                for ack_line in edi_transaction_line_ids:
                    acknowledgment_line_dict = {'LineItemAcknowledgement': {
                        'ItemStatusCode': ack_line.ack_status_code,
                        'ItemScheduleQty': ack_line.product_uom_qty or line.product_uom_qty,
                        'ItemScheduleUOM': 'EA',
                        'ItemScheduleQualifier': line.order_id.partner_id.sps_item_schedule_qualifier or '068',
                        'ItemScheduleDate': (ack_line.product_schedule_date or line.scheduled_date).date()
                    }}
                    if ack_line.ack_status_code == LINE_REJECT:
                        acknowledgment_line_dict['Notes'] = {
                            'NoteCode': 'GEN',
                            'Note': ack_line.note
                        }
                    acknowledgment_lines.append(acknowledgment_line_dict)
            line_items.append({'LineItem': [order_line_dict] + acknowledgment_lines})
        return line_items

    ###################################
    # EDI 865 HELPER FUNCTIONS
    ###################################

    def create_edi_865_xml(self):
        meta_dict = {'Meta': {'Version': '1.0'}}
        header_dict = self._prepare_865_edi_header()

        edi_865_dict = {'OrderChangeAck': [meta_dict, header_dict]}

        # Convert dictionary to xml
        xml = dicttoxml.dicttoxml(edi_865_dict, attr_type=False, root=False)
        xml = xml.decode("utf-8")
        xml = xml.replace('<item>', '').replace('</item>', '')
        xml = parseString(xml).toprettyxml()
        return xml

    def _prepare_865_edi_header(self):
        date_now = datetime.now().date()
        order_id = self.order_id
        ack_type = CHANGE_ACK_NO_CHANGE if self.state == APPROVE else CHANGE_ACK_REJECT
        order_header_dict = {'OrderHeader': {
            'TradingPartnerId': order_id.sps_trading_partner_id,
            'PurchaseOrderNumber': order_id.client_order_ref,
            'TsetPurposeCode': '00',
            'PurchaseOrderDate': order_id.date_order.date(),
            'AcknowledgementType': ack_type,
            'POChangeDate': self.transaction_date,
            'POChangeAcknowledgeDate': date_now,
            'CustomerOrderNumber': order_id.sps_customer_order_number if order_id.sps_customer_order_number else order_id.name,
            'Vendor': order_id.vendor_code or '',
            'Division': order_id.sps_division or '',
        }}
        dates_dict = {'Dates': {
            'DateTimeQualifier': self.partner_id.sps_requested_delivery_date_code.code,
            'Date': self.ship_date.date(),
        }} if self.ship_date else {}

        note_dict = {'Notes': {
            'NoteCode': 'GEN',
            'Note': self.note,
        }} if ack_type == CHANGE_ACK_REJECT else {}

        header_dict = {'Header': dict(**order_header_dict, **dates_dict, **note_dict)}
        return header_dict

    ###################################
    # EDI 850 HELPERS FUNCTIONS
    ###################################
    def _prepare_order_vals_from_edi_850(self, sps_850_xml):
        order = sps_850_xml.get(ORDER_TAG)
        vals = {}
        if order:
            # Parse Header vals
            header = order.get(HEADER_TAG)
            if header:
                header_vals = self._parse_850_header_vals(header)
                vals.update(header_vals)
            # Add default analytic account id
            partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
            analytic_id = self.env['account.analytic.account'].search([('partner_id', '=', partner_id.id)], limit=1)
            vals.update({'analytic_account_id': analytic_id.id})

            # Parse Line item vals
            line_items = order.get(LINE_ITEM_TAG)
            if line_items:
                partner_id = vals.get('partner_id')
                line_items = ensure_list(line_items)
                line_vals = self._parse_850_order_line_vals(line_items, partner_id)
                line_vals = {
                    'order_line': [(0, 0, line_val) for line_val in line_vals]
                }
                vals.update(line_vals)

        return vals

    def _parse_850_order_header_vals(self, order_header):
        vals = {}
        sps_trading_partner_id = order_header.get(SPS_TRADING_PARTNER_ID_PATH)

        client_order_ref = order_header.get(CLIENT_ORDER_REF)
        division = order_header.get(DIVISION, False)

        order_id = self.env['sale.order'].search([('client_order_ref', '=', client_order_ref),
                                                  ('sps_trading_partner_id', '=', sps_trading_partner_id),
                                                  ('state', 'not in', ['cancel'])])

        if order_id:
            validation_error_message = 'The Order <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a> ' \
                                       'already exists in the system' % (order_id._name, order_id.id, client_order_ref)
            raise EDITransactionValidationError(_(validation_error_message))

        date_order = order_header.get(SO_ORDER_DATE_PATH)
        vendor_code = order_header.get(VENDOR_CODE_PATH)
        sps_customer_order_number = order_header.get(CUSTOMER_ORDER_NUMBER, False)
        vals.update({
            'sps_trading_partner_id': sps_trading_partner_id,
            'client_order_ref': client_order_ref,
            'date_order': date_order,
            'vendor_code': vendor_code,
            'sps_division': division,
            'sps_customer_order_number': sps_customer_order_number if sps_customer_order_number else False
        })
        return vals

    def _parse_850_header_vals(self, header):
        """
        Parse Order information from EDI 850 Header
        :param header:
        :type header: dict
        :return:
        :rtype: dict
        """
        order_header = header.get(ORDER_HEADER_PATH)
        vals = {}
        if order_header:
            order_header_vals = self._parse_850_order_header_vals(order_header)
            vals.update(order_header_vals)

        incoterm_code = header.get(INCOTERM_PATH, {}).get(INCOTERM_CODE_PATH)
        if incoterm_code:
            incoterm_id = self.env['account.payment.term'].search([('name', '=', incoterm_code)]).id
            vals.update({'incoterm': incoterm_id})

        packaging_info = header.get(PACKAGING_PATH)
        if packaging_info:
            packaging_characteristic_code = packaging_info.get(PACKAGING_CHARACTER_PATH)
            packaging_description = packaging_info.get(PACKAGING_DESCRIPTION_PATH)
            vals.update({
                'packaging_characteristic_code': packaging_characteristic_code,
                'packaging_description': packaging_description
            })

        carrier_routing_info = header.get(CARRIER_ROUTING_INFO_PATH)
        if carrier_routing_info:
            carrier_routing = header.get(CARRIER_ROUTING_PATH)
            vals.update({'carrier_routing': carrier_routing})

        # Parse Address vals to get Shipping and Invoicing Partner
        addresses = header.get(ADDRESS_PATH)
        if addresses:
            # Cast Address to list
            addresses = ensure_list(addresses)
            address_vals = self._parse_850_address_vals(addresses)
            vals.update(address_vals)

        # Get the partner to parse the right value of schedule date
        partner_id = vals.get('partner_id')
        # Parse Date value to get Delivery Window and Schedule Date
        # (base on the date code set up for each partner)
        dates = header.get(DATE_LIST_PATH)
        if dates:
            dates = ensure_list(dates)
            date_vals = self._parse_850_date_vals(dates, partner_id)
            vals.update(date_vals)

        payment_term = header.get(PAYMENT_TERM_PATH, {}).get(TERM_DESCRIPTION_PATH)
        payment_term_vals = self._parse_850_payment_term_vals(payment_term, partner_id)
        vals.update(payment_term_vals)

        return vals

    def _parse_850_payment_term_vals(self, payment_term, partner_id):
        """
        Get SO payment term from SPS 850 header
        :rtype: dict
        """
        payment_term_id = self.env['account.payment.term'].search([('name', '=', payment_term)]).id \
            if payment_term else False
        # Get the default payment term instead
        if not payment_term_id and partner_id:
            partner_id = self.env['res.partner'].browse(partner_id)
            payment_term_id = partner_id.property_payment_term_id.id

        vals = {'payment_term_id': payment_term_id}

        return vals

    def _parse_850_date_vals(self, dates, partner_id):
        """
        Get SO addresses from SPS 850 header
        :param dates:
        :type dates: list(dict)
        :return:
        :rtype: dict
        """
        # Get dict(key:DateQualifier, value:Date)
        rec = dict(list(map(lambda date: (date.get(DATE_QUALIFIER_PATH), date.get(DATE_PATH)), dates)))

        # Get the delivery window and schedule date code qualifier which has setup on partner
        # and using it to get the value from above dict
        partner_id = self.env['res.partner'].browse(partner_id)
        sps_delivery_window_start_date = rec.get(partner_id.sps_delivery_window_start_date_code.code)
        sps_delivery_window_end_date = rec.get(partner_id.sps_delivery_window_end_date_code.code)
        sps_requested_delivery_date = rec.get(partner_id.sps_requested_delivery_date_code.code)

        vals = {
            'sps_delivery_window_start_date': sps_delivery_window_start_date,
            'sps_delivery_window_end_date': sps_delivery_window_end_date,
            'commitment_date': sps_requested_delivery_date,
        }

        return vals

    def _parse_850_address_vals(self, addresses):
        """
        Parsing Order Address vals
        :param addresses:
        :type addresses: list
        :return:
        :rtype: dict
        """
        partner_id = False
        partner_shipping_id = False
        partner_invoice_id = False
        for address in addresses:
            address_type_code = address.get(ADDRESS_TYPE_CODE_PATH)
            address_location_number = address.get(ADDRESS_LOCATION_NUMBER_PATH)
            address_name = address.get(ADDRESS_NAME_PATH)
            if address_type_code not in [ADDRESS_TYPE_SHIP_TO, ADDRESS_TYPE_BILL_TO_PARTY, ADDRESS_TYPE_BUYING_PARTY]:
                continue
            domain = []
            # Check address from Odoo side, using location number or name of address
            if address_location_number:
                domain = expression.OR([domain, [('address_location_number', '=', address_location_number)]])
            if address_name:
                domain = expression.OR([domain, [('name', '=', address_name)]])

            partner_id_temp = False
            if domain:
                partner_id_temp = self.env['res.partner'].search(domain)
                partner_id_temp = partner_id_temp and partner_id_temp[0]

            # Using partner temp to temporary store partner, then using address code to decide type of partner
            # (Shipping, Invoicing, etc.)
            if partner_id_temp:
                if address_type_code == ADDRESS_TYPE_SHIP_TO:
                    partner_shipping_id = partner_id_temp.id
                    partner_id = partner_id_temp.parent_id.id or partner_id_temp.id
                elif address_type_code in [ADDRESS_TYPE_BILL_TO_PARTY, ADDRESS_TYPE_BUYING_PARTY]:
                    partner_invoice_id = partner_id_temp.id
            else:
                if address_location_number:
                    validation_error_message = "Need to update the location number %s for Partner %s" \
                                               % (address_location_number, address_name or "")
                else:
                    validation_error_message = "Cannot find Partner %s in the system" % address_name
                raise EDITransactionValidationError(_(validation_error_message))

        # If Invoicing partner is not found, using the Partner as default
        partner_invoice_id = partner_invoice_id or partner_id

        vals = {
            'partner_shipping_id': partner_shipping_id,
            'partner_invoice_id': partner_invoice_id,
            'partner_id': partner_id,
        }
        return vals

    def _parse_850_order_line_vals(self, line_items, partner_id):
        vals = []
        error_messeage_queue = []
        counter = 1
        for item in line_items:
            order_line = item.get('OrderLine')
            if order_line:
                sps_sequence_number = order_line.get(LINE_SEQUENCE_NUMBER_TAG, counter)
                default_code = order_line.get(DEFAULT_CODE_TAG, '')
                customer_product_code = order_line.get(CUSTOMER_PRODUCT_CODE_TAG, '')

                product_id = False
                if default_code:
                    product_id = self.env['product.product'].search([('default_code', '=', default_code)])
                if customer_product_code and not product_id:
                    product_id = self.env['product.customerinfo'].search([('partner_id', '=', partner_id),
                                                                          ('product_name', '=',
                                                                           customer_product_code)]).product_id
                if not product_id:
                    error_messeage_queue.append(_(
                        "Wrong VendorPartNumber %s or BuyerPartnumber %s for line %s, please correct it." % (
                            default_code, customer_product_code, sps_sequence_number)))

                if error_messeage_queue:
                    continue
                product_id = product_id[0]

                if customer_product_code:
                    product_customer_infos = product_id.buyer_ids.filtered(lambda rec: rec.partner_id == partner_id)
                    if not product_customer_infos:
                        product_customer_infos.create({
                            'product_id': product_id.id,
                            'partner_id': partner_id,
                            'product_name': customer_product_code
                        })

                price_unit = float(order_line.get(PRICE_UNIT_TAG))
                product_uom_qty = float(order_line.get(PRODUCT_UOM_QTY_TAG))
                vals.append({
                    'sps_sequence_number': sps_sequence_number,
                    'product_id': product_id.id,
                    'product_uom_qty': product_uom_qty,
                    'price_unit': price_unit
                })
                counter += 1
        if error_messeage_queue:
            raise EDITransactionValidationError('\n'.join(error_messeage_queue))

        return vals

    ###################################
    # EDI 860 HELPERS FUNCTIONS
    ###################################
    def _prepare_order_change_from_edi_860(self, edi_860_dict):
        """
        Prepare the Order change values from edi 860
        :param edi_860_dict:
        :type edi_860_dict: dict
        :return: PO Change vals
        :rtype: dict
        """
        order_change = edi_860_dict.get(ORDER_CHANGE_TAG, {})
        vals = {}
        if order_change:
            header = order_change.get(HEADER_TAG, {})
            # Parse Header value
            if header:
                header_vals = self._parse_860_header_vals(header)
                vals.update(header_vals)

                # Parse line item values
                line_items = order_change.get(LINE_ITEM_TAG)
                line_items = ensure_list(line_items)
                order_id = vals.get('order_id')
                if line_items:
                    line_item_vals = self._parse_860_line_item_vals(order_id, line_items)
                    vals.update({'edi_transaction_line_ids': line_item_vals})
        return vals

    def _parse_860_header_vals(self, header):
        """
        Parse EDI information from 860 header
        :param header:
        :type header: dict
        :return:
        :rtype:
        """
        vals = {}
        order_header = header.get(ORDER_HEADER_PATH, {})
        client_order_ref = order_header.get(CLIENT_ORDER_REF)
        sps_trading_partner_id = order_header.get(SPS_TRADING_PARTNER_ID_PATH)

        # Check if the Order already exists in the system
        order_id = False
        if client_order_ref and sps_trading_partner_id:
            order_id = self.env['sale.order'].search([('client_order_ref', '=', client_order_ref),
                                                      ('sps_trading_partner_id', '=', sps_trading_partner_id),
                                                      ('state', 'not in', ['cancel'])])

        if not order_id:
            validation_error_message = "Order %s does not exist" % client_order_ref
            raise EDITransactionValidationError(_(validation_error_message))

        transaction_date = order_header.get(PO_CHANGE_DATE)
        vals.update({
            'order_id': order_id.id,
            'type': PO_CHANGE,
            'transaction_date': transaction_date
        })

        return vals

    def _parse_860_line_item_vals(self, order_id, line_items):
        """
        Parsing line item value from EDI 860
        :param order_id: The Original Order
        :type order_id:  int
        :param line_items:
        :type line_items:  list
        :return:
        :rtype: dict
        """
        line_vals = []
        order_id = self.env['sale.order'].browse(order_id)
        error_messeage_queue = []
        for item in line_items:
            order_line = item.get(ORDER_LINE_TAG)

            # Parse date value
            dates = item.get(DATE_LIST_PATH)
            dates = ensure_list(dates)

            # Get the schedule date by mapping with code of date with partner date code
            sps_requested_delivery_date_code = order_id.partner_id.sps_requested_delivery_date_code.code
            delivery_date = list(filter(
                lambda date: date.get(DATE_QUALIFIER_PATH) == sps_requested_delivery_date_code, dates))
            delivery_date = (delivery_date and delivery_date[0].get(DATE_PATH)) or False

            # Parse line item value
            sps_sequence_number = order_line.get(LINE_SEQUENCE_NUMBER_TAG)
            default_code = order_line.get(DEFAULT_CODE_TAG)
            customer_product_code = order_line.get(CUSTOMER_PRODUCT_CODE_TAG)
            price_unit = order_line.get(PRICE_UNIT_TAG)
            change_status_code = order_line.get(LINE_CHANGE_STATUS_CODE_TAG)

            # Get the Order Line from Odoo that maps with the EDI Line items
            order_line_id = order_id.order_line.filtered(
                lambda line: line.sps_sequence_number == sps_sequence_number
                             or line.product_id.default_code == default_code)
            order_line_id = order_line_id and order_line_id[0]

            # If the Order Line exist, update the sequence number for the Order line.
            # If it does not exits, there is a case that the PO Change request to add new line item,
            # we need to check new line item product with the Odoo system product
            product_id = False
            if order_line_id:
                if not order_line_id.sps_sequence_number:
                    order_line_id.write({'sps_sequence_number': sps_sequence_number})
            else:
                if default_code:
                    product_id = self.env['product.product'].search([('default_code', '=', default_code)]).id
                if customer_product_code and not product_id:
                    product_id = self.env['product.customerinfo'].search([('partner_id', '=', order_id.partner_id),
                                                                          ('product_name', '=',
                                                                           customer_product_code)]).product_id.id
                if not product_id:
                    error_messeage_queue.append(_(
                        "Wrong VendorPartNumber %s or BuyerPartnumber %s for line %s, please correct it." % (
                            default_code or '', customer_product_code or '', sps_sequence_number)))

            product_uom_qty = order_line.get(PRODUCT_UOM_QTY_TAG)
            line_vals.append((0, 0, {
                'sps_sequence_number': sps_sequence_number,
                'order_line_id': order_line_id.id,
                'product_id': product_id,
                'old_product_uom_qty': order_line_id.product_uom_qty,
                'product_uom_qty': product_uom_qty,
                'product_schedule_date': delivery_date,
                'change_status_code': change_status_code,
                'old_price_unit': order_line_id.price_unit,
                'price_unit': price_unit
            }))

        if error_messeage_queue:
            raise EDITransactionValidationError('\n'.join(error_messeage_queue))

        return line_vals

    ###################################
    # HELPERS FUNCTIONS
    ###################################
    def get_vals_from_edi(self, edi_data, doc_type):
        """
        Return the vals and the model need to sync with Odoo base on EDI transaction type
        :param edi_data: Parsed EDI data
        :type edi_data: dict
        :param doc_type: type of document (850,855,etc.)
        :type doc_type: str
        :return: Return vals and model need to sync on
        :rtype: (dict, str)
        """
        vals = {}
        sync_model = False
        if doc_type == PO:
            vals = self._prepare_order_vals_from_edi_850(edi_data)
            sync_model = 'sale.order'
        elif doc_type == PO_CHANGE:
            vals = self._prepare_order_change_from_edi_860(edi_data)
            sync_model = 'edi.transaction'
        return vals, sync_model
