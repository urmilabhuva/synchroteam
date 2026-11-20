# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class JobJob(models.Model):
    _name = 'job.description.template'
    _description = 'Description template for Job'

    name = fields.Char('Template Name', required=True)
    description = fields.Text('Description')
