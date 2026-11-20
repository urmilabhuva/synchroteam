# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class JobTag(models.Model):
	_name = 'job.job.tag'
	_description = 'Job Tag'

	name = fields.Char('Name')