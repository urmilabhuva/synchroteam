# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProjectTask(models.Model):
	_inherit = 'project.task'

	job_id = fields.Many2one('job.job', string='JOB')
	job_task_released = fields.Boolean('Job Task Released', default=False)
	job_task_in_alert = fields.Boolean('Job Task Alert', default=False)
	need_to_perform_task = fields.Boolean('Need to be performed before Job', default=False)

	def write(self, vals):
		if vals.get('stage_id'):
			stage = self.env['project.task.type'].browse(vals.get('stage_id'))
			if stage.is_closed:
				vals.update({'job_task_released': True})
				vals.update({'job_task_in_alert': False})
			else:
				vals.update({'job_task_released': False})
		return super(ProjectTask, self).write(vals)
