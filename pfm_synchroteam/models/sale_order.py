# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from urllib.parse import urljoin, urlencode
import requests
import base64
import json
import pytz
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit='sale.order'

    manufacture_ids = fields.One2many('mrp.production', 'job_id', compute='_compute_related_manufacturing_orders', string="Manufacturing Orders")
    manufacture_count = fields.Integer(compute='_compute_related_manufacturing_orders', string="# Manufacturing Orders")
    installation_date = fields.Date(string='Installation Date')
    has_draft_jobs = fields.Boolean('Has Draft Jobs', compute='_compute_has_draft_jobs')


    @api.onchange('partner_shipping_id')
    def onchange_partner_shipping_id(self):
        res = super(SaleOrder, self).onchange_partner_shipping_id()
        for order in self:
            order.partner_installation_id = order.partner_shipping_id
        return res

    @api.depends('job_ids')
    def _compute_related_manufacturing_orders(self):
        for order in self:
            mos = None
            for job in order.job_ids:
                for mo in job.manufacture_ids:
                    mos |=  mo
            order.manufacture_ids = mos
            if mos:
                order.manufacture_count = len(mos)

    def _compute_has_draft_jobs(self):
        self.ensure_one()
        amount_draft_jobs = self.order_line.filtered(lambda p: p.job_id and p.job_id.status == 'draft' and p.job_id.job_type_id.sent_to_st)
        if amount_draft_jobs:
            self.has_draft_jobs = True
        else:
            self.has_draft_jobs = False

    @api.depends('job_ids')
    def get_job_cnt_count(self):
        for job in self:
            if job.job_ids:
                job.jobs_count = len(job.job_ids)

    ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket')
    job_ids = fields.One2many('job.job', 'order_id', string='Jobs')
    validation_job_ids = fields.One2many('job.job', 'order_id', domain=[('require_approval', '=', True)], string='Validation Jobs')
    jobs_count = fields.Integer(string='Job Count', compute='get_job_cnt_count', store=True)
    # state = fields.Selection([
    #     ('draft', 'Quotation'),
    #     ('sent', 'Quotation Sent'),
    #     ('validation', 'Validation'),
    #     ('sale', 'Sales Order'),
    #     ('done', 'Locked'),
    #     ('cancel', 'Cancelled'),
    # ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    state = fields.Selection(
        selection_add=[('validation', 'Validation'), ('sent',)])

    @api.constrains('job_ids')
    def _validate_job_country(self):
        for sale in self:
            country_ids = [x.site_id.country_id for x in sale.job_ids]
            countrys = set(country_ids)
            if len(countrys) > 1:
                raise ValidationError(_('An order can only contain jobs for 1 installation country.'))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(SaleOrder, self).create(vals_list)
        for order in orders:
            if order.order_line:
                for line in order.order_line:
                    if line.job_id:
                        line.job_id.order_id = line.order_id
            if order.ticket_id:
                msg = _("Quotation %s created for ticket.") % order.name
                order.ticket_id.message_post(body=msg)
        # for vals in vals_list:
        #     if vals.get('order_line'):
        #         order_line_data = vals.get('order_line')
        #         for line in order_line_data:
        #             if line[2]:
        #                 if line[2].get('job_id'):
        #                     job_id = line[2].get('job_id')
        #                     job = self.env['job.job'].browse(job_id)
        #                     job.order_id = result.id
        # if result.ticket_id:
        #     msg = _("Quotation %s created for ticket.") % result.name
        #     result.ticket_id.message_post(body=msg)
        return orders

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        if vals.get('state'):
            state_change = vals.get('state')
            if state_change == 'cancel':
                for job in self.job_ids:
                    job.status = 'cancelled'
        if vals.get('order_line'):
            order_line_data = vals.get('order_line')
            for line in order_line_data:
                if line[2]:
                    if line[2].get('job_id'):
                        job_id = line[2].get('job_id')
                        job = self.env['job.job'].browse(job_id)
                        job.order_id = self.id
        return result

    @api.onchange('partner_installation_id')
    def onchange_jobs(self):
        for order in self:
            if order.job_ids:
                country_ids = [x.site_id.country_id for x in order.job_ids]
                countries = set(country_ids)
                if self.partner_installation_id.country_id not in countries:
                    raise ValidationError(_('All jobs should have the same installation location country.'))

    @api.depends('type_id')
    def onchange_type_id(self):
        for order in self:
            for job in order.job_ids:
                job.job_type_id = order.type_id.job_type_id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        result = super(SaleOrder, self).onchange_partner_id()
        for line in self.order_line:
            line.job_id = None
        return result

    def action_validate(self):
        result = super(SaleOrder, self).action_confirm()
        for line in self.order_line:
            if not line.job_id.estimation_date:
                if self.installation_date:
                    line.job_id.estimation_date = self.installation_date
                else:
                    line.job_id.estimation_date = '2099-01-01'
        self.send_to_st()
        if not self.state == 'sale':
            self.write({'state': 'sale'})
        for line in self.order_line:
            if line.job_id and not line.job_id.validation_user_id:
                line.job_id.validation_user_id = self.env.user.id
        return result

    def action_draft(self):
        result = super(SaleOrder, self).action_draft()
        for job in self.job_ids.filtered(lambda p: p.job_type_id and p.job_type_id.sent_to_st):
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
            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'action_draft', 'request_url': url})
            job_result = json.loads(response.text)
            if job_result.get('id'):
                job.status = 'draft'
                return result
            elif job_result.get('status') == 'cancelled':
                job.status = 'exception'
                raise UserError(_('Remove job %s from ST first.') %job.name)
            else:
                job.status = 'draft'
                return result

    def action_confirm(self):
        for line in self.order_line:
            if line.job_id:
                if line.product_id.route_ids:
                    manufacture_true = False
                    make_to_order_true = False
                    kit_bom = [x for x in line.product_id.bom_ids if x.type == 'phantom']
                    for route in line.product_id.route_ids:
                        if route.name == 'Manufacture':
                            manufacture_true = True
                        if route.name == 'Make To Order':
                            make_to_order_true = True
                    if manufacture_true and not make_to_order_true and not kit_bom:
                        raise Warning(_(
                            'Manufacturing product %s should be set as make2order since it will be used in a job.') % line.product_id.name)
                if not line.job_id.estimation_date:
                    if self.installation_date:
                        line.job_id.estimation_date = self.installation_date
                    else:
                        line.job_id.estimation_date = '2099-01-01'

        if self.validation_job_ids:
            self.write({'state': 'validation'})
        elif not self.validation_job_ids:
            self.send_to_st()
            for line in self.order_line:
                if line.job_id:
                    line.job_id.validation_user_id = self.env.user.id
            result = super(SaleOrder, self).action_confirm()
            return result

    def send_to_st(self):
        timezone = pytz.timezone(self._context.get('tz') or 'UTC')
        domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
        if not domain:
            raise UserError(_('Set domain for ST synchronization'))
        api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
        if not api_key:
            raise UserError(_('Set API key for ST synchronization'))
        bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
        headers = {'Authorization': "Basic %s " % bearer_token_64, "Accept": "text/json",
                   "Content-Type": "application/json", "cache-control": "no-cache"}

        #Check Jobs and add to dict
        job_ids = []
        for line in self.order_line:
            if line.job_id and line.job_id.status == 'draft' and line.job_id.job_type_id.sent_to_st:
                if line.job_id in job_ids:
                    continue
                else:
                    job_ids.append(line.job_id)

        #Get product quantity
        for job in job_ids:
            # Custom Fields
            custom_field_value = {}
            customfieldvalues = []
            if job.custom_field_ids:
                for custom_field in job.custom_field_ids:
                    custom_field_value = {}
                    custom_field_value['label'] = custom_field.name.name
                    custom_field_value['value'] = custom_field.value
                    customfieldvalues.append(custom_field_value)

            custom_field_value_location = {}
            if job.location_id:
                object_url = "/web#id=%s&view_type=form&model=pfm.locaties&action=876&menu_id=549"
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                cmdb_url = object_url % (job.location_id.id)
                url = urljoin(base_url, cmdb_url)
                custom_field_value_location['label'] = 'CMDB URL'
                custom_field_value_location['value'] = url
                customfieldvalues.append(custom_field_value_location)
            # Constraints
            if not job.job_type_id and (not job.job_type_id.st_job_type_id or job.job_type_id.st_job_type_id == 0):
                raise UserError('Map the job type for this job to ST.')

            #Customer Send
            if (not job.site_id.st_partner_id or job.site_id.st_partner_id == 0):
                customer_url = 'https://ws.synchroteam.com/api/v3/customer/details'
                querystring = {'name':job.site_id.name}
                payload = ""
                cust_response = requests.request("GET", customer_url, data=payload, headers=headers, params=querystring)
                cust_result = json.loads(cust_response.text)
                if cust_result.get('id'):
                    id_value = int(cust_result['id'])
                    job.site_id.write({'st_partner_id': id_value})
                else:
                    url = "https://ws.synchroteam.com//api/v3/customer/send"
                    tags = []
                    if job.site_id.category_id:
                        for category in job.site_id.category_id:
                            tags.append(category.name)
                    if not job.site_id.partner_longitude or not job.site_id.partner_latitude:
                        job.site_id.geo_localize()


                    lat = str(job.site_id.partner_latitude).replace(',', '.')
                    long = str(job.site_id.partner_longitude).replace(',', '.')
                    #raise UserError(_('%s %s.') % (lat, long))
                    if job.site_id:
                        myId = ("ID:" + str(job.site_id.id))
                        if job.site_id.ref:
                            myId = myId + str("/REF:" + job.site_id.ref)
                    else:
                        myId = ''
                    if job.site_id:
                        addr = job.site_id._display_address()
                    else:
                        addr = ''
                    # if job.site_id and job.site_id.state_id and job.site_id.country_id:
                    #     addr = job.site_id.street + ', ' + job.site_id.city + ', ' + job.site_id.state_id.name + ', ' + job.site_id.zip + ', ' + job.site_id.country_id.name
                    # elif job.site_id and job.site_id.country_id:
                    #     addr = job.site_id.street + ', ' + job.site_id.city + ', ' + job.site_id.zip + ', ' + job.site_id.country_id.name
                    # else:
                    #     addr = ''
                    payload_dict_partner = {
                        "address": addr,
                        "adressStreet": job.site_id.street or '',
                        "adressCity": job.site_id.city or '',
                        "adressProvince": job.site_id.state_id.name if job.site_id.state_id else '',
                        "adressZIP": job.site_id.zip or '',
                        "adressCountry": job.site_id.country_id.name if job.site_id.country_id else '',
                        "contactEmail": job.site_id.email or '',
                        "contactFirstName": job.contact_firstname or '',
                        "contactLastName": job.contact_lastname or '',
                        "contactPhone": job.site_id.phone or job.site_id.mobile or '',
                        "myId": myId,
                        "name": job.site_id.name,
                        # "site": {"name": job.site_id.name},
                        "position":{
                            "latitude": lat,
                            "longitude": long,
                        },
                        "tags" : tags
                    }
                    payload = json.dumps(payload_dict_partner)
                    response = requests.request("POST", url, data=payload, headers=headers)
                    model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                    self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_to_st', 'request_url': url})
                    value = json.loads(response.text)
                    id_value = int(value['id'])
                    job.site_id.write({'st_partner_id': id_value})

            #  Add Parts to job
            part_list = []
            delivery = self.env['stock.picking'].search([('job_id', '=', job.id), ('state', 'not in', ('cancel', 'draft')), ('picking_type_id','in', [2,7,12,22,27,32,37,42,47,82,85,91])], limit=1)
            # if not delivery:
            #     raise ValidationError(_('No delivery found for job'))
            product_dict = {}
            for line in delivery.move_ids_without_package.filtered(lambda m: m.state not in ('cancel', 'draft')):
                if line.product_id.id not in job.product_ids.ids and line.product_id.type != 'service':
                    job.product_ids = [(4, line.product_id.id)]

                product = line.product_id
                if product.type != 'service':
                    if not product.default_code or product.default_code == '':
                        raise UserError(_('Product %s has no reference set, please set one.') % product.name)
                    if product.st_id == 0:
                        prod_url = "https://ws.synchroteam.com/api/v3/part/details"
                        querystring = {'reference': product.default_code}
                        payload = ""
                        prod_response = requests.request("GET", prod_url, data=payload, headers=headers, params=querystring)
                        prod_result = json.loads(prod_response.text)
                        if prod_result.get('id'):
                            product.st_id = int(prod_result.get('id'))
                            flag = True
                            for list in part_list:
                                if list.get('id') == product.st_id:
                                    list['quantity'] = list['quantity'] + line.product_uom_qty
                                    flag = False
                            if flag:
                                product_dict = {}
                                product_dict['id'] = product.st_id
                                product_dict['reference'] = product.default_code
                                product_dict['quantity'] = line.product_uom_qty
                                product_dict['serialNumbers'] = None
                                part_list.append(product_dict)
                        else:
                            tax = product.taxes_id
                            if not tax:
                                if line.sale_line_id.tax_id:
                                    tax = line.sale_line_id.tax_id

                            # Create part
                            url = "https://ws.synchroteam.com/api/v3/part/send"

                            if tax and tax.st_tax_id:
                                payload_dict_part = {
                                "name": product.name,
                                "reference": product.default_code,
                                "description": product.default_code,
                                "price": product.list_price,
                                "isTracked": False,
                                "isSerializable": False,
                                "category": {
                                    "name": product.categ_id.name,
                                },
                                "tax": {
                                    "id": tax.st_tax_id,
                                }
                                }
                            else:
                                payload_dict_part = {
                                "name": product.name,
                                "reference": product.default_code,
                                "description": product.default_code,
                                "price": product.list_price,
                                "isTracked": False,
                                "isSerializable": False,
                                "category": {
                                    "name": product.categ_id.name,
                                },
                                "tax": None,
                                }
                            payload = json.dumps(payload_dict_part)
                            response = requests.request("POST", url, data=payload, headers=headers)
                            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_to_st', 'request_url': url})
                            value = json.loads(response.text)
                            product.st_id = int(value.get('id'))
                            flag = True
                            for list in part_list:
                                if list.get('id') == product.st_id:
                                    list['quantity'] = list['quantity'] + line.product_uom_qty
                                    flag = False
                            if flag:
                                product_dict = {}
                                product_dict['id'] = product.st_id
                                product_dict['reference'] = product.default_code
                                product_dict['quantity'] = line.product_uom_qty
                                product_dict['serialNumbers'] = None
                                part_list.append(product_dict)
                    else:
                        # Create part list
                        flag = True
                        for list in part_list:
                            if list.get('id') == product.st_id:
                                list['quantity'] = list['quantity'] + line.product_uom_qty
                                flag = False
                        if flag:
                            product_dict = {}
                            product_dict['id'] = product.st_id
                            product_dict['reference'] = product.default_code
                            product_dict['quantity'] = line.product_uom_qty
                            product_dict['serialNumbers'] = None
                            part_list.append(product_dict)

            est_time = '2099-01-01'

            #Preferences
            if job.estimation_date:
                est = job.estimation_date
                est = pytz.UTC.localize(fields.Datetime.from_string(est))
                est = est.astimezone(timezone)
                est_time = est.strftime('%Y-%m-%d')

            pref_list = []
            preferences_dict = {}
            preferences_dict['date'] = est_time
            preferences_dict['isDraft'] = True
            if self.company_id.st_id:
                preferences_dict['team'] = {'id': self.company_id.st_id, 'name': self.company_id.st_name}
            payload_dict = {
                # "idCustomer": str(job.site_id.st_partner_id),
                "customer": {"id":job.site_id.st_partner_id},
                #"idJobType": str(job.job_type_id.st_job_type_id),
                "type": {"name": job.job_type_id.name},
                # "nmJobType": job.job_type_id.name,
                "myId": job.name,
                "description": job.description,
                #"login": job.mechanic,
                "customFieldValues": customfieldvalues,
                "parts": part_list,
                "priority": job.priority,
                # "status": job.status,
                "status": 'created',
                #"validation_user": validation_user,
                #nmValidation
                "preferences": preferences_dict,
            }

            if job.street2:
                payload_dict.update({'addressComplement': job.street2})
            if job.street:
                payload_dict.update({'adressStreet': job.street})
            if job.zip:
                payload_dict.update({'adressZIP': job.zip})
            if job.city:
                payload_dict.update({'adressCity': job.city})
            if job.state_id:
                payload_dict.update({'adressProvince': job.state_id.name})
            if job.country_id:
                payload_dict.update({'adressCountry': job.country_id.name})
            if job.contact_phone:
                payload_dict.update({'contactPhone': job.contact_phone})
            if job.contact_mobile:
                payload_dict.update({'contactMobile': job.contact_mobile})
            if job.contact_email:
                payload_dict.update({'contactEmail': job.contact_email})
            url = "https://ws.synchroteam.com/api/v3/job/send"
            payload = json.dumps(payload_dict)
            response = requests.request("POST", url, data=payload, headers=headers)
            model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
            self.env['synchroteam.log'].create({'record_id': self.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_to_st', 'request_url': url})
            job_result = json.loads(response.text)
            job.payload_stored = payload
            if job_result.get('id') : #and  int(job_result.get('id')) != 0
                job.write({'status': 'created'})
                delivery_ids = self.env['stock.picking'].search([('job_id', '=', job.id), ('state', 'not in', ('cancel', 'draft')), ('picking_type_id','in', [2,7,12,22,27,32,37,42,47,82,85,91])])
                for delivery in delivery_ids:
                    scheduled_date = job.estimation_date if job.estimation_date else est_time
                    delivery.write({'scheduled_date': scheduled_date})
                    date_deadline = scheduled_date + timedelta(days=1)
                    delivery.write({'date_deadline': date_deadline})
                self.write({'state': 'sale'})

            else:
                message = ''
                if job_result['message']:
                    message = job_result['message']
                if message:
                    raise UserError(_('Your job can not be created in ST due to: %s') % message)
                else:
                    raise UserError(_('Your job can not be created in ST. Please contact your system administrator.'))

    def job_action_views(self):
        action = self.env.ref('pfm_synchroteam.action_job_model').read()[0]
        job = self.job_ids
        if len(job) > 1:
            action['domain'] = [('id', 'in', job.ids)]
        elif job:
            action['views'] = [(self.env.ref('pfm_synchroteam.job_job_form').id, 'form')]
            action['res_id'] = job.id
        else:
            action['domain'] = [('id', 'in', job.ids)]
        action['context'] = {
            'default_order_id': [self.id],
        }
        return action