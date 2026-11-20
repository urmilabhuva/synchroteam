# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    default_team_helpdesk_orders = fields.Boolean('Default Team for Helpdesk Orders', copy=False)