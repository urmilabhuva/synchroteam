# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    job_id = fields.Many2one('job.job', string='Job')
    job_picking_released = fields.Boolean('Job Picking Released', default=False)
    job_picking_in_alert = fields.Boolean('Job Picking Alert', default=False)
    mechanic = fields.Char(string='Job Mechanic', related='job_id.mechanic', store=True)
    job_picking_notes = fields.Text('Job Picking Notes',related='job_id.picking_notes')

    def write(self, vals):
        if vals.get('state'):
            if vals.get('state') == 'done':
                vals.update({'job_picking_released': True})
                vals.update({'job_picking_in_alert': False})
        if vals.get('date_done'):
            vals.update({'job_picking_released': True})
            vals.update({'job_picking_in_alert': False})
        return super(StockPicking, self).write(vals)
