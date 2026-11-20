# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import requests
from datetime import datetime, timedelta
import base64


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	st_url = fields.Char('Authentication URL')
	st_domain = fields.Char('Domain URL')
	st_api_key = fields.Char('API Key for Authorisation')
	last_checked_datetime = fields.Datetime('Next Execution Job Date')

	def test_st_connection(self):
		message = ''
		if self.st_domain and self.st_api_key:
			try:
				url = self.env['ir.config_parameter'].sudo().get_param(
				'pfm_synchroteam.st_url')
				domain = self.env['ir.config_parameter'].sudo().get_param(
				'pfm_synchroteam.st_domain')
				api_key = self.env['ir.config_parameter'].sudo().get_param(
				'pfm_synchroteam.st_api_key')
				bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
				headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
				response = requests.get(url, headers=headers)
				model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
				self.env['synchroteam.log'].create({'record_id': '', 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'test_st_connection', 'request_url': url})
				if response.status_code == 200:
					message = "Login authentication successful...!\n"
					view = self.env.ref('pfm_synchroteam.sh_message_wizard')
					view_id = view and view.id or False
					context = dict(self._context or {})
					context['message'] = "Login authentication successful...!\n"
					name = 'Success'		
				else:
					message = "Login Failed...!\n"
					view = self.env.ref('pfm_synchroteam.sh_message_wizard')
					view_id = view and view.id or False
					context = dict(self._context or {})
					context['message'] = "Login Failed...!\n"
					name="Falied"
				return {
						'name': name,
						'type': 'ir.actions.act_window',
						'view_type': 'form',
						'view_mode': 'form',
						'res_model': 'sh.message.wizard',
						'views': [(view.id, 'form')],
						'view_id': view.id,
						'target': 'new',
						'context': context,
					}

			except Exception as e:
				message += str(e)
			raise UserError(_('%s') % message)

	def set_values(self):
		super(ResConfigSettings, self).set_values()
		params = self.env['ir.config_parameter'].sudo()
		params.set_param('pfm_synchroteam.st_url', self[0].st_url)
		params.set_param('pfm_synchroteam.st_domain', self[0].st_domain)
		params.set_param('pfm_synchroteam.st_api_key', self[0].st_api_key)

	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		params = self.env['ir.config_parameter'].sudo()
		res.update(
			st_url=params.get_param('pfm_synchroteam.st_url', default=''),
			st_domain=params.get_param('pfm_synchroteam.st_domain', default=''),
			st_api_key=params.get_param('pfm_synchroteam.st_api_key', default=''),
			)
		return res
