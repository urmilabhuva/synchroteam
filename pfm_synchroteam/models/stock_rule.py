# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockRule(models.Model):
	_inherit = 'stock.rule'

	def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
		result = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
		if result.get('job_id'):
			job = result.get('job_id')
			if type(job) == int:
				job_id = self.env['job.job'].browse(job)
			else:
				job_id = job
			if job_id.delivery_address:
				result.update({'job_id': job_id.id, 'partner_id': job_id.delivery_address.id})
		return result

	def _get_custom_move_fields(self):
		fields = super(StockRule, self)._get_custom_move_fields()
		fields += ['job_id']
		fields += ['pfm_location_id']
		return fields

	def _make_po_get_domain(self, company_id, values, partner):
		domain = super(StockRule, self)._make_po_get_domain(company_id, values, partner)
		gpo = self.group_propagation_option
		group = (gpo == 'fixed' and self.group_id) or \
				(gpo == 'propagate' and 'group_id' in values and values['group_id']) or False

		if values.get('job_id'):
			domain += (
				('job_id', '=', values['job_id'].id),
			)
		if group:
			domain += (('group_id', '=', group.id),)
		return domain

	def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
		result = super(StockRule, self)._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
		if values.get('job_id'):
			result.update({'job_id': values['job_id'].id})
		return result


	def _prepare_purchase_order(self, company_id, origins, values):
		result = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
		for val_each in values:
			if val_each.get('job_id'):
				result.update({'job_id': val_each['job_id'].id})
		return result
