# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
	_inherit = 'stock.move'

	job_id = fields.Many2one('job.job', string='Job')

	@api.model
	def _prepare_merge_moves_distinct_fields(self):
		distinct_fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
		distinct_fields.append('job_id')
		return distinct_fields

	@api.model
	def _prepare_merge_move_sort_method(self, move):
		move.ensure_one()
		keys_sorted = super(StockMove, self)._prepare_merge_move_sort_method(move)
		keys_sorted.append(move.job_id.id)
		return keys_sorted


	def _prepare_procurement_values(self):
		vals = super(StockMove, self)._prepare_procurement_values()
		if self.job_id:
			vals.update({'job_id': self.job_id})
		if self.pfm_location_id:
			vals.update({'pfm_location_id': self.pfm_location_id.id})
		return vals

	def _key_assign_picking(self):
		keys = super(StockMove, self)._key_assign_picking()
		if self.job_id:
			keys += (self.job_id, )
		return keys

	def _search_picking_for_assignation(self):
		self.ensure_one()
		picking = self.env['stock.picking'].search([
				('group_id', '=', self.group_id.id),
				('location_id', '=', self.location_id.id),
				('location_dest_id', '=', self.location_dest_id.id),
				('picking_type_id', '=', self.picking_type_id.id),
				('printed', '=', False),
				('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned']),
				('job_id', '=', self.job_id.id)], limit=1)

		return picking

	def _get_new_picking_values(self):
		result = super(StockMove, self)._get_new_picking_values()
		result.update({'job_id': self.job_id.id})
		return result
