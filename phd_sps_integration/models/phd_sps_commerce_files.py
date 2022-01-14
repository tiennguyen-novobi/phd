from odoo import api, fields, models
import logging
import paramiko
import base64
import os.path
from datetime import datetime as dt
from ast import literal_eval
from odoo.addons.phd_sps_integration.models.edi_transaction import PO, PO_CHANGE, PO_PREFIX, PO_CHANGE_PREFIX

_logger = logging.getLogger(__name__)

DOC_TYPE_BY_CODE = {
    PO_PREFIX: PO,
    PO_CHANGE_PREFIX: PO_CHANGE
}

DOC_CODE_LENGTH = 2

DOC_SEND_TO_SPS_TYPE = ['810', '855', '865']


class PHDSPSCommerceFiles(models.Model):
    _name = "phd.sps.commerce.file"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Name")
    upload_download_time = fields.Datetime()
    last_modify_on_remote = fields.Datetime()
    document_type = fields.Selection(
        selection=[('850', 'Order (850)'), ('810', 'Invoice (810)'), ('855', 'Order Ack (855)'),
                   ('860', 'Order Change (860)'), ('865', 'Order Change Ack (865)')])
    last_imported = fields.Datetime()
    is_imported = fields.Boolean()
    last_exported = fields.Datetime()
    is_exported = fields.Boolean()
    sync_status = fields.Selection(selection=[('pending', 'Pending'), ('done', 'Done'), ('error', 'Error')], tracking=True)
    origin = fields.Char()
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade')
    unique = fields.Char()

    def get_sps_file_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        record_url = '{base_url}/web#id={file_id}&model={model}&view_type={view_type}'.format(
            base_url=base_url,
            file_id=self.id,
            model=self._name,
            view_type='form'
        )

        return record_url

    @api.model
    def _sftp_config(self):
        return {
            'host': self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_ip_host_name', ""),
            'username': self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_user_name', ""),
            'password': self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_password', ""),
            'port': self.env['ir.config_parameter'].sudo().get_param('phd_sps_intergration.sftp_port', 22),
        }

    def action_pending(self):
        self.ensure_one()
        self.write({'sync_status': 'pending'})

    @api.model
    def _sps_sftp_server(self):
        sftp_config = self._sftp_config()
        is_connection = False
        if sftp_config:
            ip = sftp_config['host']
            username = sftp_config['username']
            password = sftp_config['password']
            port = sftp_config['port']
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(ip, port, username, password)
                is_connection = True
            except Exception as e:
                _logger.exception('SPS SFTP Server connection failed: %s' % str(e))
            return is_connection, ssh

    def _change_dir(self, dir, sftp):
        list_dir = dir.split('/')
        successful = False
        sftp.chdir()
        for dir in list_dir:
            try:
                sftp.chdir(dir)
                successful = True
            except Exception:
                successful = False
        return successful

    @api.model
    def _fetch_order(self):
        is_connection, ssh = self._sps_sftp_server()
        dirs = [
            {
                'dir': self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_out_path', "")
            },
        ]
        for dir in dirs:
            if is_connection:
                if dir['dir'] != "":
                    sftp = ssh.open_sftp()
                    if self._change_dir(dir=dir['dir'], sftp=sftp):
                        today = fields.Datetime.now()
                        for temp in sftp.listdir_attr():
                            if os.path.splitext(temp.filename)[1] != '':
                                doc_type = DOC_TYPE_BY_CODE.get(temp.filename[:DOC_CODE_LENGTH])
                                unique = dir['dir'] + '/' + temp.filename
                                file = self.env['phd.sps.commerce.file'].search([('unique', '=', unique)], limit=1)
                                if not file:
                                    datetime = fields.datetime.now()
                                    attachment = self.env['ir.attachment'].create({
                                        'name': temp.filename,
                                        'type': 'binary',
                                        'datas': base64.b64encode(sftp.open(temp.filename).read()),
                                    })

                                    if attachment:
                                        values = {
                                            'name': os.path.splitext(temp.filename)[0],
                                            'upload_download_time': datetime,
                                            'last_modify_on_remote': dt.fromtimestamp(temp.st_mtime),
                                            'sync_status': 'pending',
                                            'document_type': doc_type,
                                            'unique': dir['dir'] + '/' + temp.filename,
                                            'attachment_id': attachment.id,
                                        }
                                    sps_file = self.env['phd.sps.commerce.file'].create(values)
                                    sps_file.message_subscribe(partner_ids=sps_file._get_sps_followers())
                                if file and (today - dt.fromtimestamp(temp.st_mtime)).days >= 1:
                                    sftp.remove(unique)
                            self._cr.commit()
                    sftp.close()

    def _get_sps_followers(self):
        partner_ids = self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sps_message_follower_ids',
                                                                       "")
        partner_ids = literal_eval(partner_ids)
        return partner_ids

    @api.model
    def action_send_edi_to_sps(self, file_to_sync=False):
        is_connection, ssh = self._sps_sftp_server()

        dir = self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_in_path', "")

        if not file_to_sync:
            file_to_sync = self.search([('sync_status', 'not in', ['done']),
                                        ('document_type', 'in', DOC_SEND_TO_SPS_TYPE)])

        now_datetime = dt.now()
        if is_connection:
            sftp = ssh.open_sftp()
            if self._change_dir(dir=dir, sftp=sftp):
                for file in file_to_sync:
                    # Upload file to SPS
                    sftp.put(file.attachment_id._full_path(file.attachment_id.store_fname).replace("\\", "/"),
                             remotepath=file.attachment_id.name)
                    file.update({
                        'sync_status': 'done',
                        'upload_download_time': now_datetime,
                        'last_modify_on_remote': now_datetime,
                    })
                    self._cr.commit()
            sftp.close()

    @api.model
    def create_edi_file_send_to_sps(self, doc):
        """
        Create EDI file in Odoo, prepare for sync with SPS
        :param doc:
        :type doc: dict
        :return:
        :rtype:
        """
        send_to_sps_dir = self.env['ir.config_parameter'].sudo().get_param('phd_sps_integration.sftp_in_path', "")
        fname = doc.get('name')
        fdata = base64.b64encode(bytes(doc.get('data'), 'utf-8'))
        doc_type = doc.get('doc_type')

        # Extra vals like origin or exported, imported time
        extra_vals = doc.get('vals')

        uniq_fname = send_to_sps_dir + '/' + fname
        file = self.env['phd.sps.commerce.file'].search([('unique', '=', uniq_fname)], limit=1)
        # If file already exist, just update the data in file
        if file:
            file.attachment_id.update({
                'datas': fdata
            })
        else:
            now_datetime = dt.now()
            attachment = self.env['ir.attachment'].create({
                'name': fname,
                'type': 'binary',
                'datas': fdata
            })

            vals = {
                'name': fname,
                'last_exported': now_datetime,
                'sync_status': 'pending',
                'document_type': doc_type,
                'unique': uniq_fname,
                'attachment_id': attachment.id,
            }
            vals.update(extra_vals)
            file = self.env['phd.sps.commerce.file'].create(vals)

        return file

    def action_mark_done(self):
        for record in self:
            record.write({'sync_status': 'done'})
