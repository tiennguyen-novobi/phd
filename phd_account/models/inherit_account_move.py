# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import dicttoxml
import re
import os
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DS
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DSD
from lxml import etree
from xml.dom.minidom import parseString
from odoo.exceptions import ValidationError
import tempfile

SPS_INVOICE_DOC_TYPE = '810'
SPS_INVOICE_DOC_PREFIX = 'IN'


class AccountMove(models.Model):
    _inherit = 'account.move'

    ###################################
    # FIELDS
    ###################################
    order_id = fields.Many2one('sale.order', string="Sales Order", copy=False)
    sps_trading_partner_id = fields.Char('SPS Trading Partner ID', related='order_id.sps_trading_partner_id')
    sps_po_number = fields.Char('SPS Trading Partner ID', copy=False)
    sps_edi_document = fields.Many2one('phd.sps.commerce.file', string='EDI Document',
                                       compute='_compute_sps_edi_document')
    sps_edi_document_upload_status = fields.Selection(related='sps_edi_document.sync_status',
                                                      string='EDI Document Upload Status')
    ship_date = fields.Date('SPS Ship Date')
    bol_number = fields.Char('SPS Bill Of Lading')
    via = fields.Char('Via')
    wsi_number = fields.Char('WSI#')

    def _compute_sps_edi_document(self):
        for record in self:
            origin = 'account.move,%s' % record.id
            sps_document_id = self.env['phd.sps.commerce.file'].search(
                [('document_type', '=', '810'), ('origin', '=', origin
                                                 )], limit=1)
            if sps_document_id:
                record.sps_edi_document = sps_document_id
            else:
                record.sps_edi_document = False

    def _prepare_invoice_810_header(self):
        invoice = self
        sps_trading_partner_id = \
            invoice.sps_trading_partner_id or 'Test'

        po_date = invoice.order_id and invoice.order_id.date_order.date()
        ship_date = invoice.order_id.commitment_date and invoice.order_id.commitment_date.date()

        header_dict = {'Header':
                           [{
                               'InvoiceHeader': {
                                   'TradingPartnerId': sps_trading_partner_id,
                                   'InvoiceNumber': invoice.name,
                                   'InvoiceDate': invoice.invoice_date,
                                   'PurchaseOrderDate': po_date,
                                   'PurchaseOrderNumber': invoice.sps_po_number,
                                   'BuyersCurrency': invoice.currency_id and invoice.currency_id.name,
                                   'BillOfLadingNumber': invoice.bol_number or '',
                                   'CustomerOrderNumber':
                                       invoice.order_id and invoice.order_id.sps_customer_order_number or invoice.order_id.name or '',
                                   'ShipDate': ship_date or ''
                               }},
                               {'PaymentTerms': {
                                   'TermsType': '01',
                                   'TermsBasisDateCode': '3',
                                   'TermsNetDueDays': (
                                           invoice.invoice_date_due - invoice.invoice_date).days,
                                   'TermsDescription': invoice.invoice_payment_term_id and invoice.invoice_payment_term_id.name,
                               }},
                               {'FOBRelatedInstruction': {
                                   'FOBPayCode': invoice.invoice_incoterm_id.code or ''
                               }},
                           ] + [self._prepare_invoice_810_address(rec[0], rec[1]) for rec in
                                [('BT', invoice.partner_id),
                                 ('ST', invoice.partner_shipping_id),
                                 ('VN', invoice.company_id)]] +
                           [{
                               'QuantityTotals': {
                                   'QuantityTotalsQualifier': 'SQT',  # Summary Quantity Totals
                                   'Quantity': len(invoice.invoice_line_ids)
                               }
                           }]
                       }
        if invoice.order_id.vendor_code:
            header_dict['Header'][0]['InvoiceHeader'].update({'Vendor': invoice.order_id.vendor_code})
        return header_dict

    def _prepare_invoice_810_address(self, code, res_obj):
        address = {'Address': {
            'AddressTypeCode': code,
            'AddressName': res_obj.name or '',
            'Address1': res_obj.street or '',
            'Address2': res_obj.street2 or '',
            'City': res_obj.city or '',
            'State': res_obj.state_id.code or '',
            'PostalCode': res_obj.zip or '',
            'Country': res_obj.country_id.code or '',
        }}
        if isinstance(res_obj, type(self.env['res.partner'])):
            address['Address'].update({'AddressLocationNumber': res_obj.address_location_number or ''})
        return address

    def _prepare_invoice_810_lines(self):
        lineitem_lst = []
        for line in self.invoice_line_ids:
            partner_id = self.partner_id.parent_id or self.partner_id
            product_alias_name = line.product_id.buyer_ids.filtered(
                lambda info: info.partner_id == partner_id)

            product_alias_name = product_alias_name and product_alias_name[0].product_name

            lineitem_dict = {'LineItem': {}}
            invoiceline_dict = {'InvoiceLine': {
                'LineSequenceNumber': line.sale_line_ids and line.sale_line_ids[0].sps_sequence_number or '',
                'BuyerPartNumber': product_alias_name,
                'VendorPartNumber': line.product_id.default_code,
                'EAN': line.product_id.barcode or '',
                'UPCCaseCode': line.product_id.case_upc or '',
                'PurchasePrice': line.price_unit,
                'ShipQty': line.quantity,
                'ExtendedItemTotal': line.price_unit * line.quantity,
                'ShipQtyUOM': 'EA',
            },
                'ProductOrItemDescription': {
                    'ProductCharacteristicCode': '08',
                    'ProductDescription': line.name,
                },
            }
            lineitem_dict.get('LineItem').update(invoiceline_dict)
            lineitem_lst.append(lineitem_dict)

        return lineitem_lst

    def create_text_810(self):
        processed = 0
        sps_file_processor = self.env['phd.sps.commerce.file']

        for invoice in self:
            invoices_list = {'Invoices': []}

            # initialize
            invoice_dict = {'Invoice': []}
            # 1. Header Line - one line for the order
            meta_dict = {'Meta': {'Version': '1.0'}}

            invoice_dict['Invoice'].append(meta_dict)
            header_dict = invoice._prepare_invoice_810_header()
            invoice_dict['Invoice'].append(header_dict)
            # LineItems

            lineitems_list = invoice._prepare_invoice_810_lines()

            invoice_dict['Invoice'] += lineitems_list

            # Summary
            summary_dict = {'Summary': {
                'TotalAmount': invoice.amount_total
            }
            }
            invoice_dict.get('Invoice').append(summary_dict)

            invoices_list.get('Invoices').append(invoice_dict)
            processed += 1

            # Convert dictionary to xml
            xml = dicttoxml.dicttoxml(invoices_list, attr_type=False, root=False)
            xml = xml.decode("utf-8")
            xml = xml.replace('<item>', '').replace('</item>', '')
            xml = xml.replace('<item>', ''). \
                replace('<Invoices>',
                        '<?xml version="1.0" encoding="utf-8"?>'). \
                replace('</Invoices>', '')
            filename = SPS_INVOICE_DOC_PREFIX + invoice.name + '.xml'
            filename = filename.replace('/', '_')
            xml = parseString(xml).toprettyxml()
            fd_vals = {'name': filename,
                       'data': xml,
                       'doc_type': SPS_INVOICE_DOC_TYPE,
                       'vals': {
                           'origin': "%s,%s" % (self._name, self.id)
                       }}
            sps_file_processor.create_edi_file_send_to_sps(fd_vals)

        return processed

    def action_create_text_810(self):
        """ Creates a new 810 and puts it into the outbox
        """
        for invoice in self:
            if not invoice.sps_trading_partner_id:
                raise ValidationError(_('Invoice %s is not SPS invoice, please uncheck it' % invoice.name))
            if invoice.state in ['draft', 'cancel', 'paid']:
                raise ValidationError(_('Invoice %s need in Post state to Upload to SPS' % invoice.name))

        self.create_text_810()

    def action_post(self):
        for move in self:
            res = True
            if move.invoice_line_ids:
                lines = move.invoice_line_ids.filtered(lambda x: not x.analytic_account_id or not x.analytic_tag_ids)
                if lines and not self._context.get('is_post', False):
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'phd.tag.analytic',
                        'target': 'new',
                        'view_id': self.env.ref('phd_account.phd_tag_analytic_view_form').id,
                    }
                else:
                    res = super(AccountMove, self).action_post()
            else:
                res = super(AccountMove, self).action_post()

            return res

    def _get_invoice_reference(self):
        res = super(AccountMove, self)._get_invoice_reference()
        if self.purchase_id:
            res = []
        return res
