# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools import config
from odoo.sql_db import TestCursor
from collections import OrderedDict
from odoo.exceptions import UserError, AccessError
import os
import PyPDF2
import logging
import tempfile
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
	_inherit = 'stock.picking'
	
	operating_unit_id = fields.Many2one('operating.unit', related='sale_id.operating_unit_id')


class IrActionsReport(models.Model):
	_inherit = 'ir.actions.report'

	def _render_qweb_pdf(self, res_ids=None, data=None):
		report_data = None
		if not data:
			data = {}
		data.setdefault('report_type', 'pdf')

		# remove editor feature in pdf generation
		data.update(enable_editor=False)

		# In case of test environment without enough workers to perform calls to wkhtmltopdf,
		# fallback to render_html.
		if (tools.config['test_enable'] or tools.config['test_file']) and not self.env.context.get('force_report_rendering'):
			return self._render_qweb_html(res_ids, data=data)

		# As the assets are generated during the same transaction as the rendering of the
		# templates calling them, there is a scenario where the assets are unreachable: when
		# you make a request to read the assets while the transaction creating them is not done.
		# Indeed, when you make an asset request, the controller has to read the `ir.attachment`
		# table.
		# This scenario happens when you want to print a PDF report for the first time, as the
		# assets are not in cache and must be generated. To workaround this issue, we manually
		# commit the writes in the `ir.attachment` table. It is done thanks to a key in the context.
		context = dict(self.env.context)
		if not config['test_enable']:
			context['commit_assetsbundle'] = True

		# Disable the debug mode in the PDF rendering in order to not split the assets bundle
		# into separated files to load. This is done because of an issue in wkhtmltopdf
		# failing to load the CSS/Javascript resources in time.
		# Without this, the header/footer of the reports randomly disapear
		# because the resources files are not loaded in time.
		# https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
		context['debug'] = False

		# The test cursor prevents the use of another environnment while the current
		# transaction is not finished, leading to a deadlock when the report requests
		# an asset bundle during the execution of test scenarios. In this case, return
		# the html version.
		if isinstance(self.env.cr, TestCursor):
			return self.with_context(context)._render_qweb_html(res_ids, data=data)[0]

		save_in_attachment = OrderedDict()
		if self.report_name == 'sale.report_saleorder_copy_2':
			try:
				file_path = get_module_resource('pfm_sale', 'tests', 'Man_Registrationheadsets_30102018-compressed.pdf')
				add_pdf_file = open(file_path, 'rb')
				content = add_pdf_file.read()
				add_pdf_file.close()
				report_data = content
			except AccessError:
				_logger.info("Cannot save PDF report")


		if res_ids:
			# Dispatch the records by ones having an attachment and ones requesting a call to
			# wkhtmltopdf.
			Model = self.env[self.model]
			record_ids = Model.browse(res_ids)
			wk_record_ids = Model
			if self.attachment:
				for record_id in record_ids:
					attachment_id = self.retrieve_attachment(record_id)
					if attachment_id:
						save_in_attachment[record_id.id] = attachment_id
					if not self.attachment_use or not attachment_id:
						wk_record_ids += record_id
			else:
				wk_record_ids = record_ids
			res_ids = wk_record_ids.ids

		# A call to wkhtmltopdf is mandatory in 2 cases:
		# - The report is not linked to a record.
		# - The report is not fully present in attachments.
		if save_in_attachment and not res_ids:
			_logger.info('The PDF report has been generated from attachments.')
			return self._post_pdf(save_in_attachment), 'pdf'

		if self.get_wkhtmltopdf_state() == 'install':
			# wkhtmltopdf is not installed
			# the call should be catched before (cf /report/check_wkhtmltopdf) but
			# if get_pdf is called manually (email template), the check could be
			# bypassed
			raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

		html = self.with_context(context)._render_qweb_html(res_ids, data=data)[0]

		# Ensure the current document is utf-8 encoded.
		html = html.decode('utf-8')
		if self.report_name != 'sale.report_saleorder_copy_2':

			bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(context)._prepare_html(html)

			if self.attachment and set(res_ids) != set(html_ids):
				raise UserError(_("The report's template '%s' is wrong, please contact your administrator. \n\n"
					"Can not separate file to save as attachment because the report's template does not contains the attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.") %  self.name)

			pdf_content = self._run_wkhtmltopdf(
				bodies,
				header=header,
				footer=footer,
				landscape=context.get('landscape'),
				specific_paperformat_args=specific_paperformat_args,
				set_viewport_size=context.get('set_viewport_size'),
			)
			if res_ids:
				_logger.info('The PDF report has been generated for records %s.' % (str(res_ids)))
				return self._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=html_ids), 'pdf'
			return pdf_content, 'pdf'
		else:
			if res_ids:
				bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(context)._prepare_html(html)

				pdf_content = self._run_wkhtmltopdf(
					bodies,
					header=header,
					footer=footer,
					landscape=context.get('landscape'),
					specific_paperformat_args=specific_paperformat_args,
					set_viewport_size=context.get('set_viewport_size'),
				)

				if report_data:
					fd, file_name = tempfile.mkstemp()
					fd2, file_name2 = tempfile.mkstemp()
					fd3, file_name3 = tempfile.mkstemp()
					os.write(fd2, report_data)
					os.write(fd, pdf_content)
					output = PyPDF2.PdfFileWriter()
					pdfTwo = PyPDF2.PdfFileReader(open(file_name2, "rb"))
					pdfOne = PyPDF2.PdfFileReader(open(file_name, "rb"))
					pgcnt=pdfOne.getNumPages()
					for i in range(0,pgcnt):
						output.addPage(pdfOne.getPage(i))
					pgcnt=pdfTwo.getNumPages()
					for i in range(0,pgcnt):
						output.addPage(pdfTwo.getPage(i))
					outputStream = open(file_name3, "wb")
					output.write(outputStream)
					outputStream.close()
					f = open('%s'%(file_name3),'rb')
					content_new = f.read()
					f.close()

					_logger.info('The PDF report has been generated for records %s.' % (str(res_ids)))
					return self._post_pdf(save_in_attachment, pdf_content=content_new, res_ids=res_ids), 'pdf'
			  
