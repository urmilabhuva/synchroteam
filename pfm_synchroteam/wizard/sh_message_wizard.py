# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ShMessageWizard(models.TransientModel):
    _name="sh.message.wizard"
    _description ='ST Message Wizard'
    
    def get_default(self):
        if self.env.context.get("message",False):
            return self.env.context.get("message")
        return False 

    name=fields.Text(string="Message",readonly=True,default=get_default)
