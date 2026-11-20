# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CustomerAgreement(models.Model):
	_name = 'customer.agreement'
	_description = "Customer Agreements"
	_rec_name = 'code'


	code = fields.Char('Agreement Code')
	partner_id = fields.Many2one('res.partner', string="Customer")
	po_number = fields.Char('PO Number')
	start_date = fields.Date('Start Date')
	end_date = fields.Date('End Date')
	max_amount = fields.Float('Max. Amount')
	amount_used = fields.Float('Amount Used')
	note = fields.Text(string='Description')

	@api.model
	def create(self, vals):
		if 'code' not in vals or vals['code'] == _('New'):
			vals['code'] = self.env['ir.sequence'].next_by_code('quality.point') or _('New')
		return super(CustomerAgreement, self).create(vals)
