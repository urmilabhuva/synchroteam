# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, timedelta



class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	@api.depends('job_id')
	def _get_job_status(self):
		for job in self:
			if job.job_id:
				job.job_status = job.job_id.status
			else:
				job.job_status = 'None'

	job_id = fields.Many2one('job.job', string='Job', copy=False)
	is_job = fields.Boolean('Is Job', default=False)
	job_status = fields.Char('Job Status', compute='_get_job_status', store=True)

	@api.onchange('job_id')
	def job_apply(self):
		if self.job_id:
			self.is_job = True
		else:
			self.is_job = False

	def write(self, vals):
		if vals.get('product_uom_qty') == 0:
			jobs = []
			for line in self.order_id.order_line:
				if line == self:
					continue
				else:
					if line.product_uom_qty != 0:
						jobs.append(line.job_id)
		return super(SaleOrderLine, self).write(vals)

	def _prepare_procurement_values(self, group_id=False):
		vals = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
		if self.job_id:
			vals.update({'job_id': self.job_id.id})
			if self.route_id:
				vals.update({'route_ids': self.route_id})
			else:
				vals.update({'route_ids': self.job_id.order_id.warehouse_id.two_step_location or self.order_id.warehouse_id.two_step_location})
		if self.job_id.estimation_date:
			vals.update({'date_planned': self.job_id.estimation_date})
			vals.update({'date_deadline': self.job_id.estimation_date + timedelta(days=1)})
		if self.location_id:
			vals.update({'pfm_location_id': self.location_id.id})
		return vals

	def unlink(self):
		res = False 
		for line_current in self:
			job_id = []
			for line in line_current.order_id.order_line:
				if line.id != line_current.id and line.job_id and line.job_id.id not in job_id:
					job_id.append(line.job_id.id)
			if not job_id:
				job = line_current.job_id
				if job:
					job.order_id = False
					job.status = '8'
			res = super(SaleOrderLine, line_current).unlink()
		return res

	def _timesheet_create_task_prepare_values(self, project):
		result = super(SaleOrderLine, self)._timesheet_create_task_prepare_values(project)
		result.update({'job_id': self.job_id.id})
		result.update({'date_deadline': self.job_id.estimation_date,
					   'need_to_perform_task': self.product_id.need_to_perform_task})
		return result