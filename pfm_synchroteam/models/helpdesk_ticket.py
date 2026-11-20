# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskTicket(models.Model):
	_inherit = 'helpdesk.ticket'

	@api.depends('order_ids')
	def get_sale_cnt_count(self):
		for ticket in self:
			ticket.sale_count=0
			if ticket.order_ids:
				ticket.sale_count = len(ticket.order_ids)

	order_ids = fields.One2many('sale.order', 'ticket_id', string='Quotations')
	sale_count = fields.Integer('Quotation Count', compute='get_sale_cnt_count')

	def assign_quotation(self):

		team = self.env['crm.team'].search([('operating_unit_id', '=', self.operating_unit_id.id), ('company_id','=', self.company_id.id)], limit=1)
		team_default = self.env['crm.team'].search([('default_team_helpdesk_orders', '=', True), ('company_id','=', self.company_id.id)], limit=1)
		if not team and not team_default:
			raise ValidationError(_('No sales team found, please set a default sales team or link a sales team to an operating unit'))

		quotation = self.env['sale.order'].create({
			'partner_id': self.partner_id.parent_id.id or self.partner_id.id,
			'partner_installation_id': self.partner_id.id,
			'ticket_id': self.id,
			'operating_unit_id': self.operating_unit_id.id,
			'client_order_ref': 'Ticket: ' + self.display_name,
			'team_id': team and team.id or team_default and team_default.id

		})
		quotation.onchange_partner_id()
		quotation.partner_installation_id = quotation.partner_shipping_id

		action = self.env.ref('sale.action_orders').read()[0]

		if quotation:
			return {
				'name': _('Quotations'),
				'view_mode': 'form,tree',
				'res_model': 'sale.order',
				'type': 'ir.actions.act_window',
				'res_id': quotation.id,
			}
		return action
