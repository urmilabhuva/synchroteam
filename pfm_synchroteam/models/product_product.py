# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import requests
from datetime import datetime, timedelta
import base64
import json
import pytz
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    st_id = fields.Integer('ST Part ID')

    def send_product_to_set(self):
        domain = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_domain')
        api_key = self.env['ir.config_parameter'].sudo().get_param('pfm_synchroteam.st_api_key')
        bearer_token_64 = base64.b64encode(("%s:%s" % (domain, api_key)).encode('UTF-8')).decode('UTF-8')
        headers = {'Authorization': "Basic %s " % bearer_token_64, "Accept": "text/json", "Content-Type": "application/json", "cache-control": "no-cache"}
        for product in self:
            if product.type != 'service':
                if not product.default_code or product.default_code == '':
                    raise UserError(_('Product %s has no reference set, please set one.') % product.name)
                if product.st_id == 0:
                    _logger.info(_('Sending product to ST'))
                    # Create product category
                    st_category_id = product.categ_id.st_category_id
                    if product.categ_id and product.categ_id.st_category_id == 0:
                        url = "https://ws.synchroteam.com/Api/v1/Parts/Category/New"
                        name = product.categ_id.name
                        payload_dict_categ = {'name': name}
                        payload = json.dumps(payload_dict_categ)
                        response = requests.request("POST", url, data=payload, headers=headers)
                        model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                        self.env['synchroteam.log'].create({'record_id': product.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_product_to_set', 'request_url': url})
                        value = json.loads(response.text)
                        id_value = int(value['id'])
                        product.categ_id.st_category_id = id_value
                        st_category_id = int(value['id'])

                    # Create taxes
                    taxes = product.taxes_id
                    # for tax in taxes:
                    #     if tax.st_tax_id == 0:
                    #         url = "https://ws.synchroteam.com/Api/v1/Taxes/New"
                    #         payload_dict_tax = {
                    #             "name": tax.name,
                    #             "rate": tax.amount,
                    #             'isdefault': 0
                    #         }
                    #         payload = json.dumps(payload_dict_tax)
                    #         response = requests.request("POST", url, data=payload, headers=headers)
                    #         model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                    #         self.env['synchroteam.log'].create({'record_id': product.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_product_to_set', 'request_url': url})
                    #         value = json.loads(response.text)
                    #         tax.st_tax_id = int(value['id'])

                    # Create part
                    url = "https://ws.synchroteam.com/api/v3/part/send"
                    # url = "https://ws.synchroteam.com/Api/v2/Part/Send"
                    #with tax id
                    if taxes and taxes[0].st_tax_id:
                        payload_dict_part = {
                              "name": product.name,
                              "reference": product.default_code,
                              "description": product.default_code,
                              "price": product.list_price,
                              "isTracked": False,
                              "isSerializable": True,
                              "category": {
                                "id": st_category_id,
                                "name": product.categ_id.name,
                              },
                              "tax": {
                                "id": product.taxes_id[0].st_tax_id,
                              }
                            }
                    #with tax creation
                    if taxes and not taxes[0].st_tax_id:
                        payload_dict_part = {
                              "name": product.name,
                              "reference": product.default_code,
                              "description": product.default_code,
                              "price": product.list_price,
                              "isTracked": False,
                              "isSerializable": True,
                              "category": {
                                "id": st_category_id,
                                "name": product.categ_id.name,
                              },
                              "tax": {
                                "name": taxes[0].name,
                                "rate": taxes[0].amount
                              }
                            }
                        # payload_dict_part = {
                        #     "name": product.name,
                        #     'taxId': product.taxes_id[0].st_tax_id,
                        #     "price": product.list_price,
                        #     'categoryId': st_category_id,
                        #     "categoryName": product.categ_id.name,
                        #     "reference": product.default_code,
                        #     "myId": product.id,
                        # }
                    if not taxes:
                        payload_dict_part = {
                              "name": product.name,
                              "reference": product.default_code,
                              "description": product.default_code,
                              "price": product.list_price,
                              "isTracked": False,
                              "isSerializable": True,
                              "category": {
                                "id": st_category_id,
                                "name": product.categ_id.name,
                              },
                              "tax": None,
                            }
                        # payload_dict_part = {
                        #     "name": product.name,
                        #     "price": product.list_price,
                        #     'categoryId': st_category_id,
                        #     "categoryName": product.categ_id.name,
                        #     "reference": product.default_code,
                        #     "myId": product.id,
                        # }
                    payload = json.dumps(payload_dict_part)
                    response = requests.request("POST", url, data=payload, headers=headers)
                    model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
                    self.env['synchroteam.log'].create({'record_id': product.id, 'record_obj': model_id.id, 'datetime': datetime.now(), 'record_method': 'send_product_to_set', 'request_url': url})
                    value = json.loads(response.text)
                    tax_obj = value.get('tax')
                    if tax_obj:
                        taxes[0].st_tax_id = tax_obj['id']
                    product.st_id = int(value['id'])
