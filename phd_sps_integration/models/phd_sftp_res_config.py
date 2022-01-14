
from odoo import api, fields, models, _
import paramiko
from odoo.exceptions import UserError
from ast import literal_eval


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    sftp_ip_host_name = fields.Char(string="IP/hostname", config_parameter='phd_sps_integration.sftp_ip_host_name')
    sftp_user_name = fields.Char(string="Username", config_parameter='phd_sps_integration.sftp_user_name')
    sftp_password = fields.Char(string="Password", config_parameter='phd_sps_integration.sftp_password')
    sftp_port = fields.Integer(string="Port", config_parameter='phd_sps_intergration.sftp_port')

    sftp_in_path = fields.Char(string="EDI In Patch", config_parameter='phd_sps_integration.sftp_in_path')
    sftp_out_path = fields.Char(string="EDI Out Patch", config_parameter='phd_sps_integration.sftp_out_path')

    sps_message_follower_ids = fields.Many2many('res.partner', string='Followers (Partners)')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('phd_sps_integration.sps_message_follower_ids', self.sps_message_follower_ids.ids)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        sps_message_follower_ids = self.env['ir.config_parameter'].sudo()\
            .get_param('phd_sps_integration.sps_message_follower_ids')
        res.update(sps_message_follower_ids=[(6, 0, literal_eval(sps_message_follower_ids))] if sps_message_follower_ids else False)
        return res

    def test_sftp_connection(self):
        sftp_config = self.env['phd.sps.commerce.file']._sftp_config()
        if sftp_config:
            ip = sftp_config['host']
            username = sftp_config['username']
            password = sftp_config['password']
            port = sftp_config['port']
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(ip, port, username, password)
                ssh.close()
            except Exception as e:
                raise UserError(_('SPS SFTP Server connection failed: %s') % str(e))

        title = _("Connection Test Succeeded!")
        message = _("Everything seems properly set up!")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'sticky': False,
            }
        }