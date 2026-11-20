# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CustomFieldValues(models.Model):
	_name = 'custom.field.value'
	_description = 'Custom Field Associated to Job'

	name = fields.Many2one('custom.field', string='Name')
	value = fields.Char(string='Value')
	job_id = fields.Many2one('job.job', string='Job')


class CustomField(models.Model):
	_name = 'custom.field'
	_description = 'Custom Field'

	name = fields.Char(string='Name')
