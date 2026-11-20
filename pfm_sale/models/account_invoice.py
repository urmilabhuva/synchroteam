# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
	_inherit = 'account.move'

	user_id = fields.Many2one(tracking=False)

	def button_cancel(self):
		'''
		Method overwrite to return only to be able to execute by xmlrpc script from outside
		'''
		self.write({'auto_post': False, 'state': 'cancel'})
		return True

	def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
		if self._context.get('tracking_disable'):
			return False
		return super(AccountMove, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids,
															 subtype_ids=subtype_ids)

	def action_post(self):
		self.with_context(tracking_disable=True)._post(soft=False)
		return False

	@api.model
	def create(self, vals):
		res = super(AccountMove, self).create(vals)
		followers = self.env['mail.followers'].sudo().search(
			[('res_model', '=', self._name), ('res_id', '=', res.id)]
		)
		for follower in followers:
			follower.unlink()
		return res
class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def create(self, vals):
    	context = self._context
    	if context.get('default_type') and context.get('default_type') in ('in_invoice','in_refund','out_invoice','out_refund'):
    		vals.update({'type': 'binary'})
    	res = super(IrAttachment, self).create(vals)
    	return res