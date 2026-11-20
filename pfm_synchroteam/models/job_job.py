# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, Warning
import requests
import base64
import json
from datetime import datetime, timedelta
import pytz
from odoo.tools import float_is_zero, float_compare
import re
import logging
_logger = logging.getLogger(__name__)


class JobJob(models.Model):
    _name = 'job.job'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Job'

    def _get_address(self):
        for job in self:
            address = ''
            if job.street:
                address += job.street + ', '
            if job.city:
                address += job.city + ', '
            if job.state_id:
                address += job.state_id.code
            if job.zip:
                address += job.zip + ', '
            if job.state_id and not job.zip:
                address += ', '
            if job.country_id:
                address += job.country_id.name
            self.address = address

    @api.depends('sale_order_line_ids')
    def get_sale_order_line_count(self):
        for job in self:
            if job.sale_order_line_ids:
                job.sale_order_line_count = len(job.sale_order_line_ids)

    @api.depends('purchase_ids')
    def get_purchase_cnt_count(self):
        for job in self:
            if job.purchase_ids:
                job.purchase_count = len(job.purchase_ids)

    @api.depends('stock_picking_ids')
    def get_stock_picking_count(self):
        for job in self:
            if job.stock_picking_ids:
                job.stock_picking_count = len(job.stock_picking_ids)

    @api.depends('manufacture_ids')
    def get_manufacture_cnt_count(self):
        for job in self:
            if job.manufacture_ids:
                job.manufacture_count = len(job.manufacture_ids)

    @api.depends('task_ids')
    def get_task_count(self):
        for job in self:
            if job.task_ids:
                job.task_count = len(job.task_ids)

    @api.depends('order_id.ticket_id')
    def get_ticket_count(self):
        for job in self:
            if job.order_id:
                if job.order_id.ticket_id:
                    job.ticket_count = len(job.order_id.ticket_id)

    def get_address_street(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.street

    def get_address_street2(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.street2

    def get_address_zip(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.zip

    def get_address_city(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.city

    def get_address_state(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            if site.state_id:
                return site.state_id
            else:
                return False

    def get_address_country(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            if site.country_id:
                return site.country_id
            else:
                return False

    def get_address_phone(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.phone

    def get_address_mobile(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.mobile

    def get_address_email(self):
        if self.env.context.get('default_site_id') and self.env.context:
            site = self.env['res.partner'].browse(self.env.context.get('default_site_id'))
            return site.email

    require_approval = fields.Boolean('Require Approval', default=True)
    payload_stored = fields.Text(string="Payload")
    response_stored = fields.Text(string="Response")
    invoice_response_stored = fields.Text(string="Invoice Response")
    name = fields.Char(string='Job Number', copy=False, readonly=True, default=lambda x: _('New'))
    job_in_alert = fields.Boolean('Job In Alert', readonly=False, default=False)
    job_type_id = fields.Many2one('job.type', string='Job Type', required=False)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Customer', index=True, tracking=True, required=False, readonly=True, domain="[]")
    order_id = fields.Many2one('sale.order', string='Sale Order')
    client_order_ref = fields.Char(string='Client Order Reference', related='order_id.client_order_ref')
    site_id = fields.Many2one('res.partner', string='Installation Location', required='True')
    mechanic = fields.Char(string='Mechanic', default='To be planned')
    template_id = fields.Many2one('job.description.template', string='Template')
    description = fields.Text(string='Job Description')
    public_link = fields.Char("Public Link", readonly=True)
    priority = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],'Priority', default='medium')
    schedule_start_date = fields.Datetime(string='Schedule Start date')
    schedule_end_date = fields.Datetime(string='Schedule End Date')
    actual_start_date = fields.Datetime(string='Actual Start Date')
    actual_end_date = fields.Datetime(string='Actual End Date')
    validation_date = fields.Datetime(string='Validation Date')
    estimation_date = fields.Date(string='Estimation Date')
    duration = fields.Integer(string='Time spent working on the job, given in minutes')
    address = fields.Char(string='Address', compute='_get_address')
    street = fields.Char(string='Street', default=get_address_street)
    street2 = fields.Char(string='Street2', default=get_address_street2)
    zip = fields.Char(string='ZIP', default=get_address_zip)
    city = fields.Char(string='City', default=get_address_city)
    state_id = fields.Many2one('res.country.state', string='Province', default=get_address_state)
    country_id = fields.Many2one('res.country', string='Country', default=get_address_country)
    status = fields.Selection([('draft', 'Draft'), ('created', 'Sent'), ('scheduled', 'Planned'), ('synchronized', 'Released'), ('started', 'Started'), ('paused', 'started/paused'),
                               ('completed', 'Completed'), ('validated', 'Validated'), ('cancelled', 'Cancelled'), ('exception', 'Exception')], string='Job Status', copy=False, index=True, tracking=True, default="draft")
    validation_user_id = fields.Many2one('res.users', string='Job Validated by')
    contact_phone = fields.Char(string='Contact Phone', default=get_address_phone)
    contact_mobile = fields.Char(string='Contact Mobile', default=get_address_mobile)
    contact_email = fields.Char(string='Contact Email', default=get_address_email)
    contact_firstname = fields.Char(string='Contact Firstname')
    contact_lastname = fields.Char(string='Contact Lastname')

    product_ids = fields.Many2many('product.product', 'product_product_job_rel', 'job_id', 'product_id', string='Parts')
    custom_field_ids = fields.One2many('custom.field.value', 'job_id', string='Custom Fields Value')
    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5), related='site_id.partner_latitude')
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5), related='site_id.partner_longitude')
    tag_ids = fields.Many2many('job.job.tag', 'job_job_job_tag', string='Tags', help="Optional tags you may want to assign for custom Job")

    sale_order_line_ids = fields.One2many('sale.order.line', 'job_id', string='Sale Order Lines')
    sale_order_line_count = fields.Integer('Sale Order Line Count', compute='get_sale_order_line_count', store=True)
    purchase_ids = fields.One2many('purchase.order', 'job_id', string="Purchase Order(s)")
    purchase_count = fields.Integer('Purchase Count', compute='get_purchase_cnt_count', store=True)
    stock_picking_ids = fields.One2many('stock.picking', 'job_id', string='Stock Picking(s)')
    stock_picking_count = fields.Integer('Stock Picking(s) Count', compute='get_stock_picking_count', store=True)
    manufacture_ids = fields.One2many('mrp.production', 'job_id', string="Manufacturing Order(s)")
    manufacture_count = fields.Integer('Manufacture Count', compute='get_manufacture_cnt_count', store=True)
    task_ids = fields.One2many('project.task', 'job_id', domain=[('active','=', True)], string='Task(s)')
    task_count = fields.Integer('Task Count', compute='get_task_count', store=True)
    delivery_address = fields.Many2one('res.partner', string='Delivery Address', required=True, help="Delivery address for current Job.")
    ticket_count = fields.Integer('Ticket Count', compute='get_ticket_count', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    picking_notes = fields.Text('Picking Notes')
    auto_process_delivery = fields.Boolean('Automatic processing of delivery order', default=False)
    st_notes = fields.Text('Job Report Notes', copy=False)
    pictures_retrieved = fields.Boolean(copy=False, default=False)

    def get_helpdesk_ticket(self):
        for job in self:
            form_view_ref = self.env.ref('helpdesk.helpdesk_ticket_view_form', False)
            tree_view_ref = self.env.ref('helpdesk.helpdesk_tickets_view_tree', False)
            res_id = job.order_id.ticket_id
            return {
                'name': 'Membership Invoices',
                'res_model': 'helpdesk.ticket',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', res_id.ids)],
                'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            }

    def get_sale_order(self):
        for job in self:
            orders = job.order_id
            action_vals = {
                'name': _('Sale Order'),
                'domain': [('id', 'in', orders.ids)],
                'view_type': 'form',
                'res_model': 'sale.order',
                'view_id': False,
                'type': 'ir.actions.act_window',
            }
            if len(orders) == 1:
                action_vals.update({'res_id': orders[0].id, 'view_mode': 'form'})
            else:
                action_vals['view_mode'] = 'tree,form'
            return action_vals


    def unlink(self):
        for job in self:
            if job.order_id:
                raise ValidationError(_('You cannot delete a job related to an order.'))
            if job.status != 'cancelled':
                raise ValidationError(_('You can only delete cancelled jobs.'))
        return super(JobJob, self).unlink()

    def set_to_cancel(self):
        for job in self.filtered(lambda p: p.job_type_id and p.job_type_id.sent_to_st):
            domain = self.env['ir.config_parameter'].sudo().get_param(
                'pfm_synchroteam.st_domain')
            api_key = self.env['ir.config_parameter'].sudo().get_param(
                'pfm_synchroteam.st_api_key')
            bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
            headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
#             url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
            url = "https://ws.synchroteam.com/api/v3/job/details"
            querystring = {'myId': job.name}
            payload = ""
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': job.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
            job_result = json.loads(response.text)
            if not job_result.get('code'):
                job.status = 'cancelled'
            elif job_result.get('status') != 'cancelled':
                raise UserError(_('Cancel job %s in ST first.') %job.name)
            else:
                job.status = 'cancelled'

    @api.model_create_multi
    def create(self, vals_list):
        context= self._context
        for vals in vals_list:
            if context.get('sale_context') and vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('job.job') or _('New')
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('job.job') or _('New')
            if context.get('location'):
                location = self.env['pfm.locaties'].browse(context.get('location'))
                vals.update({'location_id': location.id})
        return super(JobJob, self).create(vals_list)

    def write(self, vals):
        result = super(JobJob, self).write(vals)

        domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
        api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
        bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
        headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
        timezone = pytz.timezone(self._context.get('tz') or 'UTC')

        #Update when state = sent
        if self.status == 'created' and self.job_type_id.sent_to_st and (vals.get('priority') or vals.get('duration')):
#             url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
            url = "https://ws.synchroteam.com/api/v3/job/details"
            querystring = {'myId': self.name}
            payload = ""
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'write', 'request_url': url})
            job_result = json.loads(response.text)
            if vals.get('priority'):
                priority = int(vals.get('priority'))
                if job_result.get('priority'):
                    if priority != job_result.get('priority'):
                        raise Warning(_('Priority is different in Synchroteam, please correct in Synchroteam first.'))
            if vals.get('duration'):
                duration = vals.get('duration')
                if job_result.get('Duration'):
                    if duration != job_result.get('Duration'):
                        raise Warning(_('Duration is different in Synchroteam, please correct in Synchroteam first.'))

        # if self.status not in ('0', '7', '8', '9') and self.job_type_id.sent_to_st:
        #     url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
        #     querystring = {'myId': self.name}
        #     payload = ""
        #     response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
        #     job_result = json.loads(response.text)

        if self.status == 'cancelled' and self.job_type_id.sent_to_st:
#             url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
            url = "https://ws.synchroteam.com/api/v3/job/details"
            querystring = {'myId': self.name}
            payload = ""
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'write', 'request_url': url})
            job_result = json.loads(response.text)
            if job_result.get('code'):
                return result
            if not job_result.get('status'):
#                 url = "https://ws.synchroteam.com/Api/v2/Jobs/Cancel"
#                 response = requests.request("PUT", url, data=payload, headers=headers, params=querystring)
                url = "https://ws.synchroteam.com/api/v3/job/cancel"
                payload_dict = {"myId": self.name}
                payload = json.dumps(payload_dict)
                response = requests.request("POST", url, data=payload, headers=headers)

            else:
                self.status = 'exception'
                # Create activity
                summary = _("Job is put in exception state since it can't be removed from Synchroteam. Please remove manually.")
                sim_activity = self.env['mail.activity'].search([
                    ('res_id', '=', self.id),
                    ('summary', '=', summary),
                ])
                if not sim_activity:
                    activity_vals = {
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'user_id': self.validation_user_id.id or self.create_uid.id,
                        'summary': summary
                    }
                    self.activity_schedule(**activity_vals)
        return result

    def set_draft(self):
        if self.job_type_id.sent_to_st:
            domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
            api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
            bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
            headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
#             url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
            url = "https://ws.synchroteam.com/api/v3/job/details"
            querystring = {'myId': self.name}
            payload = ""
            response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'set_draft', 'request_url': url})
            job_result = json.loads(response.text)
            if not job_result.get('code'):
                self.status = 'draft'
                return True
            if job_result.get('status') == 'cancelled' and self.status == 'cancelled':
                # Create activity
                summary = _("Please remove job from ST before it can be set to draft.")
                sim_activity = self.env['mail.activity'].search([
                    ('res_id', '=', self.id),
                    ('summary', '=', summary),
                ])
                if not sim_activity:
                    activity_vals = {
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'user_id': self.validation_user_id.id or self.create_uid.id,
                        'summary': summary,
                    }
                    self.activity_schedule(**activity_vals)
            if job_result.get('status') == 'cancelled' and self.status != 'cancelled':
                self.status = 'exception'
                # Create activity
                summary = _("There is an exception in the ST flow. Please check and correct.")
                sim_activity = self.env['mail.activity'].search([
                    ('res_id', '=', self.id),
                    ('summary', '=', summary),
                ])
                if not sim_activity:
                    activity_vals = {
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                        'user_id': self.validation_user_id.id or self.create_uid.id,
                        'summary': summary,
                    }
                    self.activity_schedule(**activity_vals)
        else:
            self.status = 'draft'
        return True

    @api.onchange('site_id')
    def onchange_site_id_check_country(self):
        if self.order_id and self.site_id and self.order_id.job_ids:
            jobs = self.order_id.job_ids.ids
            job_id = self._context.get('params', {}).get('id')
            if job_id:
                jobs.remove(int(job_id))
            if jobs:
                job_ids = self.browse(jobs)
                country_ids = [x.site_id.country_id for x in job_ids]
                countrys = set(country_ids)
                if self.site_id.country_id not in countrys:
                    raise ValidationError(_('All jobs related to an order should have the same installation country'))

    @api.onchange('site_id')
    def onchange_site_id(self):
        for job in self:
            if job.site_id:
                job.street = job.site_id.street
                job.street2 = job.site_id.street2
                job.zip = job.site_id.zip
                job.city = job.site_id.city
                job.state_id = job.site_id.state_id
                job.contact_phone = job.site_id.phone
                job.contact_mobile = job.site_id.mobile
                job.contact_email = job.site_id.email

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id:
            self.description = self.template_id.description

    def run_st_schedule_action(self):
        env = api.Environment(self._cr, SUPERUSER_ID, {})
        job_pool = env['job.job']
        job_pool.run_st_schedule()
#         for job in self:
#             job.run_st_schedule()

    @api.model
    def run_st_schedule(self):
        date_checked = datetime(2000, 1, 1, 0, 0, 0, 0000)
        date_checked = date_checked.strftime("%Y-%m-%d %H:%M:%S")
        actual_time = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.last_checked_datetime', default=date_checked)
        # today_d = fields.Datetime.now() - timedelta(days=100)
        # actual_time = today_d.strftime('%Y-%m-%d %H:%M:%S')
        domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
        api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
        bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
        headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        min_working_days = int(self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.min_working_days', default=0))
        #Check for jobs being planned
        jobs = self.search([('status', 'in', ['created', 'scheduled', 'synchronized', 'exception'])])
        job_ids = jobs.ids

#         url = "https://ws.synchroteam.com/Api/v2/Jobs/Search"
#         status_list_planned = ["0","1", "2"]
#         payload = json.dumps(payload_dict)
#         response = requests.request("POST", url, data=payload, headers=headers)
        job_list = []
        url = "https://ws.synchroteam.com/api/v3/job/list"
        status_list_planned = ['created', 'scheduled', 'synchronized']
        for status_li in status_list_planned:
            payload_dict = {
                "status": status_li,
                "changedSince": actual_time
                #"myId": "JOB/PFMNL/190578"
            }
            response = requests.request("GET", url, data="", headers=headers, params=payload_dict)
            job_result = json.loads(response.text)
            if job_result and job_result.get('data'):
                job_list.extend(job_result.get('data'))
        _logger.info(_('Job list %s') % job_list)
        for job in job_list:
            if job.get('myId'):
                ref_job = jobs.search([('name', '=', job.get('myId')), ('id', 'in', job_ids)])
                if ref_job:
                    _logger.info(_('Job found planned/released %s') % ref_job.name)
#                     url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
                    url = "https://ws.synchroteam.com/api/v3/job/details"
                    querystring = {'myId': ref_job.name}
                    payload = ""
                    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
                    model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                    self.env['synchroteam.log'].create({'record_id': ref_job.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                    ref_job_result = json.loads(response.text)
                    ref_job.response_stored = ref_job_result
                    if ref_job_result.get('status') == "scheduled" and ref_job.status == 'created':
                            ref_job.status = 'scheduled'
                    if ref_job_result.get('status') == "created" and ref_job.status != 'created' and ref_job.stock_picking_count != 0:
                            ref_job.status = 'created'
                    if ref_job_result.get('technician') and ref_job_result.get('technician').get('login'):
                        ref_job.mechanic = ref_job_result.get('technician').get('login')
                    if ref_job_result.get('publicLink'):
                        ref_job.public_link = ref_job_result.get('publicLink')
                    if ref_job_result.get('scheduledStart'):
                        date = ref_job_result.get('scheduledStart')
                        tz=pytz.timezone('Europe/Amsterdam')
                        #cnv_date_calc = tz.localize(datetime.strptime(date, '%d/%m/%Y %H:%M:%S'))
                        # Convert time zone
                        fmt = '%Y-%m-%d %H:%M'
                        # Current time in UTC
                        now_utc = datetime.now(pytz.timezone('UTC'))
                        # Convert to current user time zone
                        now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
                        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
                        local_datetime = datetime.strptime(date, fmt)
                        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
                        cnv_date_calc = result_utc_datetime.strftime(fmt)

                        cnv_date_calc =datetime.strptime(cnv_date_calc, '%Y-%m-%d %H:%M')
                        cnv_date = cnv_date_calc - timedelta(days=min_working_days)
                        weekday = cnv_date.weekday()
                        if weekday in [0, 1, 2, 3, 4]:
                            cnv_date = cnv_date
                        else:
                            if weekday == 5:
                                cnv_date = cnv_date - timedelta(days=1)
                            if weekday == 6:
                                cnv_date = cnv_date - timedelta(days=2)
                        ref_job.schedule_start_date = cnv_date_calc
                        delivery = self.env['stock.picking'].search([('job_id', '=', ref_job.id), ('state', 'not in', ('cancel','draft'))])
                        if delivery and ref_job.status != 'exception':
                            for pick in delivery:
                                if pick.state in ['cancel']:
                                    ref_job.status = 'exception'
                                    # Create activity
                                    summary = _("Job is in exception due to picking %s is in %s state. Please remove picking to continue.") % (pick.name, pick.state)
                                    sim_activity = self.env['mail.activity'].search([
                                        ('res_id', '=', ref_job.id),
                                        ('summary', '=', summary),
                                    ])
                                    if not sim_activity:
                                        activity_vals = {
                                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                            'user_id': ref_job.validation_user_id.id or ref_job.create_uid.id,
                                            'summary': summary,
                                        }
                                        ref_job.activity_schedule(**activity_vals)
                                    continue
                                try:
                                    pick.scheduled_date = cnv_date
                                except:
                                    pass
                        manufacture = self.env['mrp.production'].search([('job_id', '=', ref_job.id)])
                        if manufacture and ref_job.status != 'exception':
                            for manu in manufacture:
                                if manu.state in ['cancel']:
                                    ref_job.status = 'exception'
                                    # Create activity
                                    summary = _("Job is in exception due to MO %s is in %s state. Please remove MO to continue.") % (manu.name, manu.state)
                                    sim_activity = self.env['mail.activity'].search([
                                        ('res_id', '=', ref_job.id),
                                        ('summary', '=', summary),
                                    ])
                                    if not sim_activity:
                                        activity_vals = {
                                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                            'user_id': ref_job.validation_user_id.id or ref_job.create_uid.id,
                                            'summary': summary,
                                        }
                                        ref_job.activity_schedule(**activity_vals)
                                    continue
                                manu.date_planned_start = cnv_date
                        tasks = self.env['project.task'].search([('job_id', '=', ref_job.id)])
                        if tasks and ref_job.status != 'exception':
                            for task in tasks:
                                cnv_date_deadline = cnv_date.date()
                                task.date_deadline = cnv_date_deadline
                    if ref_job_result.get('scheduledEnd'):
                        end_date = ref_job_result.get('scheduledEnd')
                        # Convert time zone
                        fmt = '%Y-%m-%d %H:%M'
                        # Current time in UTC
                        now_utc = datetime.now(pytz.timezone('UTC'))
                        # Convert to current user time zone
                        now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
                        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
                        local_datetime = datetime.strptime(end_date, fmt)
                        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
                        end_schedule_date = result_utc_datetime.strftime(fmt)
                        end_schedule_date = datetime.strptime(end_schedule_date, '%Y-%m-%d %H:%M')
                        end_cnv_date = end_schedule_date - timedelta(days=min_working_days)
                        weekday = end_cnv_date.weekday()
                        if weekday in [0, 1, 2, 3, 4]:
                            end_cnv_date = end_cnv_date
                        else:
                            if weekday == 5:
                                end_cnv_date = end_cnv_date - timedelta(days=1)
                            if weekday == 6:
                                end_cnv_date = end_cnv_date - timedelta(days=2)
                        ref_job.schedule_end_date = end_schedule_date
                        delivery = self.env['stock.picking'].search([('job_id', '=', ref_job.id), ('state', 'not in', ('cancel','draft'))])
                        if delivery and ref_job.status != 'exception':
                            for pick in delivery:
                                try:
                                    pick.date_deadline = end_cnv_date
                                except:
                                    pass

                    if ref_job_result.get('report'):
                            subset = None
                            st_notes = ''
                            for item in ref_job_result['report']:
                                if item['name'] in ['Job report','Job Report']:
                                    for ite in item['items']:
                                        subset = ite
                                        if ite['name'] in ['Customer Notes','Notes']:
                                            key = subset['name']
                                            value = subset['value']
                                            st_notes = value
                                            # st_notes += st_note
                                    ref_job.st_notes = st_notes
                    # if ref_job_result.get('report'):
                    #     subset = None
                    #     for item in ref_job_result['report']:
                    #         if item['nmItem'] == 'Notes':
                    #             subset = item
                    #             value = subset['value']
                    #             ref_job.st_notes = value

        #Check for jobs started / performed
        jobs_co = self.search([('status', 'not in', ['draft', 'validated', 'cancelled'])])
        job_co_ids = jobs_co.ids
        
#         url_co = "https://ws.synchroteam.com/Api/v2/Jobs/Search"
#         status_list = [ "3", "4", "5", "6", "7"]
#         payload_dict_co = {
#             "status": status_list,
#             "changedFrom": actual_time
#             #"myId": "JOB/PFMNL/190578"
#         }
#         payload_co = json.dumps(payload_dict_co)
#         response_co = requests.request("POST", url_co, data=payload_co, headers=headers)
        # url_co = "https://ws.synchroteam.com/api/v3/job/list"
        # status_list = ['started', 'paused', 'completed', 'validated', 'cancelled']
        # payload_dict_co = {
        #     "status": status_list,
        #     "changedSince": actual_time
        #     #"myId": "JOB/PFMNL/190578"
        # }
        # response_co = requests.request("GET", url_co, data="", headers=headers, params=payload_dict_co)
        # job_list_co = json.loads(response_co.text)
        job_list_co = []
        url_co = "https://ws.synchroteam.com/api/v3/job/list"
        status_list = ['started', 'paused', 'completed', 'validated', 'cancelled']
        for status_li in status_list:
            payload_dict_co = {
                "status": status_li,
                "changedSince": actual_time
                #"myId": "JOB/PFMNL/190578"
            }
            response = requests.request("GET", url_co, data="", headers=headers, params=payload_dict_co)
            job_list_co_result = json.loads(response.text)
            if job_list_co_result and job_list_co_result.get('data'):
                job_list_co.extend(job_list_co_result.get('data'))
        _logger.info(_('Job list %s') % job_list_co)
        order_id_list = []
        for job_co in job_list_co:
            if job_co.get('myId'):
                ref_job_co = jobs_co.search([('name', '=', job_co.get('myId')), ('id', 'in', job_co_ids)])
                if ref_job_co:
                    _logger.info(_('Job found in started/performed %s') % ref_job_co.name)
#                     url = "https://ws.synchroteam.com/Api/v2/Jobs/Detail"
                    url = "https://ws.synchroteam.com/api/v3/job/details"
                    querystring = {'myId': ref_job_co.name}
                    payload = ""
                    response_co = requests.request("GET", url, data=payload, headers=headers, params=querystring)
                    model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                    self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                    ref_job_result_co = json.loads(response_co.text)
                    ref_job_co.response_stored = ref_job_result_co
                    ref_invoice_result = {}
                    if ref_job_result_co.get('status'):
                        if ref_job_result_co.get('technician') and ref_job_result_co.get('technician').get('login'):
                            ref_job_co.mechanic = ref_job_result_co.get('technician').get('login')
                        if ref_job_result_co.get('publicLink'):
                            ref_job_co.public_link = ref_job_result_co.get('publicLink')
                        if ref_job_result_co.get('actualStart'):
                            realbegindate = ref_job_result_co.get('actualStart')
                            if not realbegindate == '01/01/0001 00:00':
                            # Convert time zone
                                fmt = '%Y-%m-%d %H:%M'
                                # Current time in UTC
                                now_utc = datetime.now(pytz.timezone('UTC'))
                                # Convert to current user time zone
                                now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
                                UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
                                local_datetime = datetime.strptime(realbegindate, fmt)
                                result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
                                actual_start_date = result_utc_datetime.strftime(fmt)
                                actual_start_date = datetime.strptime(actual_start_date, '%Y-%m-%d %H:%M')
                                ref_job_co.actual_start_date = actual_start_date
                        if ref_job_result_co.get('actualEnd'):
                            realenddate = ref_job_result_co.get('actualEnd')
                            if not realenddate == '01/01/0001 00:00':
                                # Convert time zone
                                fmt = '%Y-%m-%d %H:%M'
                                # Current time in UTC
                                now_utc = datetime.now(pytz.timezone('UTC'))
                                # Convert to current user time zone
                                now_timezone = now_utc.astimezone(pytz.timezone(self.env.user.tz))
                                UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(fmt), fmt) - datetime.strptime(now_timezone.strftime(fmt), fmt)
                                local_datetime = datetime.strptime(realenddate, fmt)
                                result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
                                actual_end_date = result_utc_datetime.strftime(fmt)
                                actual_end_date = datetime.strptime(actual_end_date, '%Y-%m-%d %H:%M')
                                ref_job_co.actual_end_date = actual_end_date

                        #Process invoices manually
                        if not ref_job_co.auto_process_delivery and ref_job_co.status not in ('draft', 'validated', 'cancelled'):
                            if ref_job_result_co.get('status') == 'completed' or ref_job_result_co.get('status') == 'validated':
#                                 url = "https://ws.synchroteam.com/Api/v2/Invoices/List"
#                                 payload_dict = {'changedFrom': actual_time, 'job': {'myId': ref_job_co.name}}
#                                 payload = json.dumps(payload_dict)
#                                 response = requests.request("POST", url, data=payload, headers=headers)
                                url = "https://ws.synchroteam.com/api/v3/invoice/list"
                                querystring = {'job_myId': ref_job_co.name}
                                payload = ""
                                response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

                                model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                                self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                                ref_invoice_result = json.loads(response.text)

                                if len(ref_invoice_result.get('data')) == 0:
                                    if ref_job_result_co.get('status') == 'completed':
                                        ref_job_co.status = 'completed'
                                        # # Create activity
                                        # summary = _("Job is completed but no invoice is found.")
                                        # sim_activity = self.env['mail.activity'].search([
                                        #     ('res_id', '=', ref_job_co.id),
                                        #     ('summary', '=', summary),
                                        # ])
                                        # if not sim_activity:
                                        #     activity_vals = {
                                        #         'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                        #         'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                        #         'summary': summary
                                        #     }
                                        #     ref_job_co.activity_schedule(**activity_vals)
                                        # _logger.info(_('We post it'))
                                    elif ref_job_result_co.get('status') == 'validated':
                                        ref_job_co.status = 'completed'
                                        # Create activity
                                        summary = _("Job is validated but no invoice is created.")
                                        sim_activity = self.env['mail.activity'].search([
                                            ('res_id', '=', ref_job_co.id),
                                            ('summary', '=', summary),
                                        ])
                                        if not sim_activity:
                                            activity_vals = {
                                                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                                'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                'summary': summary
                                            }
                                            ref_job_co.activity_schedule(**activity_vals)

                                for invoice_result in ref_invoice_result.get('data'):
                                    if ref_job_result_co.get('status') == 'completed':
                                            if invoice_result.get('status') != 'paid':
                                                ref_job_co.status = 'completed'
                                                # Create activity
                                                summary = _("Job is invoiced but not validated.")
                                                sim_activity = self.env['mail.activity'].search([
                                                    ('res_id', '=', ref_job_co.id),
                                                    ('summary', '=', summary),
                                                ])
                                                if not sim_activity:
                                                    activity_vals = {
                                                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                                        'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                        'summary': summary
                                                    }
                                                    ref_job_co.activity_schedule(**activity_vals)

                            if ref_job_result_co.get('status') == "validated" and ref_job_co.status != 'validated':
#                                 url = "https://ws.synchroteam.com/Api/v2/Invoices/List"
#                                 payload_dict = {'changedFrom': actual_time, 'job': {'myId': ref_job_co.name}}
#                                 payload = json.dumps(payload_dict)
#                                 response = requests.request("POST", url, data=payload, headers=headers)
                                url = "https://ws.synchroteam.com/api/v3/invoice/list"
                                querystring = {'job_myId': ref_job_co.name}
                                payload = ""
                                response = requests.request("GET", url, data=payload, headers=headers, params=querystring)

                                model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                                self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                                ref_invoice_result = json.loads(response.text)
                                ref_job_co.invoice_response_stored = ref_invoice_result.get('data')
                                if type(ref_invoice_result.get('data')) == list:
                                    for invoice_result in ref_invoice_result.get('data'):
                                        if invoice_result.get('status') != 'paid':
                                            _logger.info(_('We find an invoice'))
                                            if ref_job_result_co.get('status') == "completed":
                                                ref_job_co.status = 'completed'
                                            if ref_job_result_co.get('status') == "validated":
                                                ref_job_co.status = 'validated'
                                            new_sale_line_total = 0
                                            for line in invoice_result.get('lines'):
                                                product_st_ids = []
                                                product_st_references = []
                                                for product in ref_job_co.product_ids:
                                                    product_st_ids.append(product.st_id)
                                                    product_st_references.append(product.default_code)

                                                name = 'Onbekend'
                                                product_url = "https://ws.synchroteam.com/Api/v2/Part/Details"
                                                if line.get('partProductCode'):
                                                    querystring = {"reference": line.get('partProductCode')}
                                                    product_response = requests.request("GET", product_url, headers=headers,
                                                                                        params=querystring)
                                                    ref_product_result = json.loads(product_response.text)
                                                    model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                                                    self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': product_url})
                                                    name = ref_product_result.get('name')
                                                    p_id = ref_product_result.get('id')
                                                    p_id = int(p_id)

                                                qty = line.get('quantity')
                                                quantity = 0
                                                if qty:
                                                    quantity = float(qty.replace(',', '.'))
                                                reference = line.get('partProductCode')
                                                price = line.get('unitPrice')
                                                price_unit = 0
                                                if price:
                                                    price_unit = float(price.replace(',', '.'))
                                                product_id = self.env['product.product'].search([('default_code', '=', line.get('partProductCode'))])

                                                if (reference not in product_st_references):
                                                    new_sale_line_total += 1
                                                    for pick in ref_job_co.stock_picking_ids:
                                                        if pick.state not in ['done', 'cancel'] and pick.picking_type_id.code == 'outgoing':
                                                            message = _('New Product: %sx - %s/ %s - EU%s ' % (
                                                            quantity, reference, name, price_unit))
                                                            pick.message_post(body=message)
                                                            pick.sale_id.message_post(body=message)
                                                            # Create activity
                                                            summary = _(
                                                                "Extra sale order line(s) need to be created for additional products")
                                                            sim_activity = self.env['mail.activity'].search([
                                                                ('res_id', '=', pick.id),
                                                                ('summary', '=', summary),
                                                            ])
                                                            if not sim_activity:
                                                                activity_vals = {
                                                                    'activity_type_id': self.env.ref(
                                                                        'mail.mail_activity_data_todo').id,
                                                                    'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                                    'summary': summary
                                                                }
                                                                pick.activity_schedule(**activity_vals)
                                                else:
                                                    for pick in ref_job_co.stock_picking_ids:
                                                        if pick.state not in ['done', 'cancel'] and pick.picking_type_id.code == 'outgoing':
                                                            message = _('Delivered %sx - %s/ %s - EU%s ' % (
                                                            quantity, reference, product_id.name, price_unit))
                                                            pick.message_post(body=message)
                                                            pick.sale_id.message_post(body=message)
                                                            # Create activity
                                                            summary = _("Delivery to customer can be processed")
                                                            sim_activity = self.env['mail.activity'].search([
                                                                ('res_id', '=', pick.id),
                                                                ('summary', '=', summary),
                                                            ])
                                                            if not sim_activity:
                                                                activity_vals = {
                                                                    'activity_type_id': self.env.ref(
                                                                        'mail.mail_activity_data_todo').id,
                                                                    'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                                    'summary': summary
                                                                }
                                                                pick.activity_schedule(**activity_vals)


                                                if not ref_job_co.stock_picking_ids and new_sale_line_total > 0:
                                                    if product_id:
                                                        # line_taxes = []
                                                        # tax = self.env['account.tax'].search(
                                                        #     [('name', '=', line.get('tax'))])
                                                        # if tax:
                                                        #     line_taxes.append(tax.id)
                                                        # route = ref_job_co.order_id.warehouse_id.one_step_location and ref_job_co.order_id.warehouse_id.one_step_location.id
                                                        # new_sale_line = self.env['sale.order.line'].create({
                                                        #     'product_id': product_id.id,
                                                        #     'name': product_id.variant_description_sale,
                                                        #     'product_uom_qty': quantity,
                                                        #     'price_unit': price_unit,
                                                        #     'job_id': ref_job_co.id,
                                                        #     'tax_id': [(6, 0, line_taxes)],
                                                        #     'order_id': ref_job_co.order_id.id,
                                                        #     'route_id': route,
                                                        # })
                                                        # new_sale_line_add.append(new_sale_line)
                                                        # ref_job_co.product_ids = [(4, product_id.id)]
                                                        message = _('New Product: %sx - %s/ %s - EU%s ' % (
                                                            quantity, reference, name, price_unit))
                                                        ref_job_co.message_post(body=message)
                                                        ref_job_co.order_id.message_post(body=message)

                                                        # Create activity
                                                        summary = _(
                                                            "Extra products added in ST need to be added to the sale order.")
                                                        sim_activity = self.env['mail.activity'].search([
                                                            ('res_id', '=', ref_job_co.id),
                                                            ('summary', '=', summary),
                                                        ])
                                                        if not sim_activity:
                                                            activity_vals = {
                                                                'activity_type_id': self.env.ref(
                                                                    'mail.mail_activity_data_todo').id,
                                                                'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                                'summary': summary
                                                            }
                                                            ref_job_co.activity_schedule(**activity_vals)

                                                    else:
                                                        message = _('New Product: %sx - %s/ %s - EU%s ' % (
                                                            quantity, reference, name, price_unit))
                                                        ref_job_co.message_post(body=message)
                                                        ref_job_co.order_id.message_post(body=message)

                                                        # Create activity
                                                        summary = _(
                                                            "Extra products added in ST need to be added to the sale order.")
                                                        sim_activity = self.env['mail.activity'].search([
                                                            ('res_id', '=', ref_job_co.id),
                                                            ('summary', '=', summary),
                                                        ])
                                                        if not sim_activity and qty:
                                                            activity_vals = {
                                                                'activity_type_id': self.env.ref(
                                                                    'mail.mail_activity_data_todo').id,
                                                                'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                                                'summary': summary
                                                            }
                                                            ref_job_co.activity_schedule(**activity_vals)

                        if ref_job_result_co.get('status') == "cancelled":
                            if ref_job_co.status == 'synchronized':
                                ref_job_co.status = 'exception'
                                # Create activity
                                summary = _("Job is put in exception state due to job is cancelled after confirmed. Please process PO/MO for further process.'")
                                sim_activity = self.env['mail.activity'].search([
                                    ('res_id', '=', ref_job_co.id),
                                    ('summary', '=', summary),
                                ])
                                if not sim_activity:
                                    activity_vals = {
                                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                        'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                        'summary': summary
                                    }
                                    ref_job_co.activity_schedule(**activity_vals)
                            else:
                                ref_job_co.status = 'exception'
                                # Create activity
                                summary = _('Job is put in exception state due to job is cancelled in ST, please check and cancel Odoo order.')
                                sim_activity = self.env['mail.activity'].search([
                                    ('res_id', '=', ref_job_co.id),
                                    ('summary', '=', summary),
                                ])
                                if not sim_activity:
                                    activity_vals = {
                                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                        'user_id': ref_job_co.validation_user_id.id or ref_job_co.create_uid.id,
                                        'summary': summary,
                                    }
                                    ref_job_co.activity_schedule(**activity_vals)

                        if ref_job_result_co.get('status') == "started":
                            ref_job_co.status = 'started'
                        if ref_job_result_co.get('status') == "paused":
                            ref_job_co.status = 'paused'

                        if ref_job_result_co.get('status') == "validated" and not ref_job_co.pictures_retrieved:
                            #Get pictures
                            url = "https://ws.synchroteam.com/api/v3/job/photos"
                            payload = ""
                            querystring = {'myId': ref_job_co.name}
                            response_photo = requests.request("GET", url, data=payload, headers=headers, params=querystring)
                            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                            self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                            photos = json.loads(response_photo.text)
                            if photos and response_photo.status_code == 200:
                                for item in photos['jobPhoto']:
                                    if item['comment'] not in ('Photos taken', 'Technician Signature', 'Customer Signature', 'Invoicing Signature'):
                                        if item['url'] and item['url'] != 'None':
                                            url = item['url']
                                            if ref_job_co.location_id:
                                                ref_job_co.location_id.message_post(body='<img src="%s" />' % url)
                                                ref_job_co.pictures_retrieved = True
                            else:
                                ref_job_co.pictures_retrieved = False

                        if ref_job_result_co.get('report'):
                            subset = None
                            st_notes = ''
                            for item in ref_job_result_co['report']:
                                if item['name'] in ['Job report','Job Report']:
                                    for ite in item['items']:
                                        subset = ite
                                        if ite['name'] in ['Customer Notes','Notes']:
                                        # if ite['name'] == 'Customer Notes' or 'Notes':
                                            key = subset['name']
                                            value = subset['value']
                                            st_notes = value
                                            # st_notes += st_note
                                    ref_job_co.st_notes = st_notes
                                if item['name'] == 'Checklist' or 'Check list':
                                    for ite in item['items']:
                                        if ite['name'] == 'Photos taken':
                                            subset = ite
                                            value = subset['value']
                                            if value == '1' and not ref_job_co.pictures_retrieved:
                                                #Get pictures
                                                url = "https://ws.synchroteam.com/api/v3/job/photos"
                                                payload = ""
                                                querystring = {'myId': ref_job_co.name}
                                                response_photo = requests.request("GET", url, data=payload, headers=headers, params=querystring)
                                                model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                                                self.env['synchroteam.log'].create({'record_id': ref_job_co.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'run_st_schedule', 'request_url': url})
                                                photos = json.loads(response_photo.text)
                                                if photos and response_photo.status_code == 200:
                                                    for item in photos['jobPhoto']:
                                                        if item['comment'] not in ('Photos taken', 'Technician Signature', 'Customer Signature', 'Invoicing Signature'):
                                                            if item['url'] and item['url'] != 'None':
                                                                url = item['url']
                                                                if ref_job_co.location_id:
                                                                    ref_job_co.location_id.message_post(body='<img src="%s" />' % url)
                                                                    ref_job_co.pictures_retrieved = True
                                                else:
                                                    ref_job_co.pictures_retrieved = False


                        # if not ref_job_co.pictures_retrieved:
                        #     #Get pictures
                        #     url = "https://ws.synchroteam.com/api/v3/job/photos"
                        #     payload = ""
                        #     querystring = {'myId': ref_job_co.name, 'getImageData': False}
                        #     response_photo = requests.request("GET", url, data=payload, headers=headers, params=querystring)
                        #     photos = json.loads(response_photo.text)
                        #     if photos and response_photo.status_code == 200:
                        #         for item in photos['jobPhoto']:
                        #             if item['comment'] not in ('Photos taken', 'Technician Signature', 'Customer Signature'):
                        #                 if item['url'] and item['url'] != 'None':
                        #                     url = item['url']
                        #                     ref_job_co.location_id.message_post(body='<img src="%s" />' % url)
                        #                     ref_job_co.pictures_retrieved = True
                        #     else:
                        #         ref_job_co.pictures_retrieved = False

        done_orders = []
        order_id_list = list(set(order_id_list))
        for order in order_id_list:
            order_done = False
            order_not_done = False
            for order_job in order.job_ids:
                if (order_job.status in ('completed', 'validated')):
                    order_done = True
                else:
                    order_not_done = True
            if order_done and not order_not_done:
                done_orders.append(order)
                order.state = 'done'

        self.env['ir.config_parameter'].sudo().set_param('pfm_synchroteam.last_checked_datetime', datetime.today())
        return True
    
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'status' in init_values and self.status == 'scheduled':
            return self.env.ref('pfm_synchroteam.mt_job_planned')
        elif 'status' in init_values and self.status == 'created':
            return self.env.ref('pfm_synchroteam.mt_job_sent')
        return super(JobJob, self)._track_subtype(init_values)

    def run_check_release_st_job(self):
        for job in self:
            job.check_release_st_job()

    @api.model
    def check_release_st_job(self):
        today_d = fields.Datetime.now()
        today_date = today_d.date()
        actual_time = today_d.strftime('%Y-%m-%d %H:%M:%S')
        jobs = self.search([('status', 'in', ('created','scheduled'))])
        jobs_list = []
        jobs_list_direct = []
        order_id_list = []
        params = self.env['ir.config_parameter'].sudo()
        min_working_days = int(params.get_param('pfm_synchroteam.min_working_days', default=0))
        for job in jobs:
            delivery_order = self.env['stock.picking'].search([('job_id', '=', job.id), ('state', 'not in', ('cancel','draft'))])
            delivery_ids = delivery_order.ids
            if delivery_ids:
                delivery = min(delivery_ids)
                delivery_order = self.env['stock.picking'].browse(delivery)
            for delivery in delivery_order:
                if delivery.job_picking_released:
                    jobs_list.append(job)
                    _logger.info(_('We add the job %s because delivery') % job.name)
                    delivery.job_picking_in_alert = False
                else:
                    delivery.job_picking_in_alert = False
                    if job in jobs_list:
                        jobs_list.pop(jobs_list.index(job))
                        _logger.info(_('We remove the job %s for delivery') % job.name)
                    if delivery.scheduled_date:
                        actual_schedule = delivery.scheduled_date - timedelta(days=min_working_days)
                        if today_d >= actual_schedule:
                            delivery.job_picking_in_alert = True
                            job.job_in_alert = True
                            # # Create activity
                            # summary = _('Delivery %s needs to be delivered to be able to process the job.' %(delivery.display_name))
                            # sim_activity = self.env['mail.activity'].search([
                            #     ('res_id', '=', job.id),
                            #     ('summary', '=', summary),
                            # ])
                            # if not sim_activity:
                            #     activity_vals = {
                            #         'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            #         'user_id': 14,
                            #         'summary': summary,
                            #     }
                            #     job.activity_schedule(**activity_vals)
            tasks = self.env['project.task'].search([('job_id', '=', job.id), ('need_to_perform_task', '=', True)])
            for task in tasks:
                if task.job_task_released:
                    jobs_list.append(job)
                    _logger.info(_('We add the job %s for task') % job.name)
                else:
                    task.job_task_in_alert = False
                    if job in jobs_list:
                        jobs_list.pop(jobs_list.index(job))
                        _logger.info(_('We remove the job %s for task') % job.name)
                    if task.date_deadline:
                        actual_date_deadline = task.date_deadline - timedelta(days=min_working_days)
                        if today_date >= actual_date_deadline:
                            task.job_task_in_alert = True
                            job.job_in_alert = True
                            # Create activity
                            summary = _("Warning: Task %s needs to be set to done to be able to process the job.") %(task.display_name)
                            sim_activity = self.env['mail.activity'].search([
                                ('res_id', '=', job.id),
                                ('summary', '=', summary),
                            ])
                            if not sim_activity:
                                activity_vals = {
                                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                    'user_id': job.validation_user_id.id or job.create_uid.id,
                                    'summary': summary,
                                }
                                job.activity_schedule(**activity_vals)
            if not tasks and not delivery_order:
                jobs_list_direct.append(job)
                _logger.info(_('We add the job %s for no task/delivery') % job.name)
        jobs_list = list(set(jobs_list))
        for job_line in jobs_list:
            if job_line.status in ('created','draft'):
                job_line.job_in_alert = True
                # # Create activity
                # summary = _('Warning: Job is ready to be performed but is not planned yet.')
                # sim_activity = self.env['mail.activity'].search([
                #     ('res_id', '=', job_line.id),
                #     ('summary', '=', summary),
                # ])
                # if not sim_activity:
                #     activity_vals = {
                #         'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                #         'user_id': job_line.validation_user_id.id or job_line.create_uid.id,
                #         'summary': summary,
                #     }
                #     job_line.activity_schedule(**activity_vals)
            elif job_line.status == 'scheduled':
                job_line.job_in_alert = False
                job_line.status = 'synchronized'

                domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
                if not domain:
                    raise UserError(_('Set domain for ST synchronization'))
                api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
                if not api_key:
                    raise UserError(_('Set API key for ST synchronization'))
                bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
                headers = {'Authorization': "Basic %s " % bearer_token_64, "Accept": "text/json",
                           "Content-Type": "application/json", "cache-control": "no-cache"}

                pref_list = []
                preferences_dict = {}
                preferences_dict['isDraft'] = False
                payload_dict = {
                    "myId": job_line.name,
                    "preferences": preferences_dict,
                }
                url = "https://ws.synchroteam.com/api/v3/job/send"
                payload = json.dumps(payload_dict)
                response = requests.request("POST", url, data=payload, headers=headers)
                model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                self.env['synchroteam.log'].create({'record_id': job_line.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'check_release_st_job', 'request_url': url})
                job_result = json.loads(response.text)
                if job_line.order_id:
                    order_id_list.append(job_line.order_id)
        jobs_list_direct = list(set(jobs_list_direct))
        for job_line_direct in jobs_list_direct:
            job_line_direct.job_in_alert = False
            job_line_direct.status = 'synchronized'

            domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
            if not domain:
                raise UserError(_('Set domain for ST synchronization'))
            api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
            if not api_key:
                raise UserError(_('Set API key for ST synchronization'))
            bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
            headers = {'Authorization': "Basic %s " % bearer_token_64, "Accept": "text/json",
                       "Content-Type": "application/json", "cache-control": "no-cache"}

            pref_list = []
            preferences_dict = {}
            preferences_dict['isDraft'] = False
            payload_dict = {
                "myId": job_line_direct.name,
                "preferences": preferences_dict,
            }
            url = "https://ws.synchroteam.com/api/v3/job/send"
            payload = json.dumps(payload_dict)
            response = requests.request("POST", url, data=payload, headers=headers)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': job_line_direct.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'check_release_st_job', 'request_url': url})
            job_result = json.loads(response.text)
            if job_line_direct.order_id:
                order_id_list.append(job_line_direct.order_id)



    def action_job_send(self):
        """ Open a window to compose an email, with the template - 'job_job'
            message loaded by default
        """
        self.ensure_one()
        template = self.env['mail.template']
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = dict(
            default_model='job.job',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            custom_layout="mail.mail_notification_light",
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def get_st_image(self):
        domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
        api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
        bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
        headers = { 'Authorization' : "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}

        for job in self:
            # Get pictures
            url = "https://ws.synchroteam.com/api/v3/job/photos"
            payload = ""
            querystring = {'myId': job.name, 'getImageData': False}
            response_photo = requests.request("GET", url, data=payload, headers=headers, params=querystring)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': job.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'get_st_image', 'request_url': url})
            photos = json.loads(response_photo.text)
            if photos and response_photo.status_code == 200:
                for item in photos['jobPhoto']:
                    if item['comment'] not in ('Photos taken', 'Technician Signature', 'Customer Signature'):
                        if item['url'] and item['url'] != 'None':
                            url = item['url']
                            if job.location_id:
                                job.location_id.message_post(body='<img src="%s" />' % url)
                                job.pictures_retrieved = True
