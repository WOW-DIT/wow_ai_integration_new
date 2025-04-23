# Copyright (c) 2024, yazan sorour and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MessageContextTemplate(Document):

	def validate(self):
		
		self.setChildren()
		self.validateReferences()
				

	def setChildren(self):
		self.context_children = []
		for row in self.text_format:
			if row.linked_field_type == "Table":

				doctype = row.target_doctype
				fields = [row.field_name, row.field_name2]

				self.append(
					"context_children",
					{
						"reference_type": doctype,
						"content": ",".join(fields),
					},
				)
		# children = frappe.get_all(doctype, fields=fields)
		# frappe.throw(str(getattr(children[0], fields[0])))


	def validateReferences(self):
		import re

		def clean_fields(field_string, symbol):
			if not isinstance(field_string, str):
				return ""
		
			if field_string is None or len(field_string.split(symbol)) == 0:
				return ""
			# Replace spaces within words (not around commas) with underscores
			cleaned = re.sub(r'(\w)\s+(?=\w)', r'\1_', field_string)
			return cleaned
		
		def validate_field(target, fields: str):
			for f in fields.split(","):
				meta = frappe.get_meta(target.reference)
				if not meta.has_field(f.strip()):
				# if frappe.Document(target.reference).meta.get_field_name_by_key_name() is None:
					frappe.throw(f"Not Found: '{f.strip()}' is not a field of '{target.reference}' DocType.")
		
		for target in self.reference_targets:
			## Validate fields
			validate_field(target, target.fields)

			empty_fields = target.filter_fields == "" or target.filter_fields is None
			empty_values = target.fields_values == "" or target.fields_values is None
			

			if not empty_fields:
				if empty_values:
					frappe.throw("You have filters without values!")
				else:
					validate_field(target, target.filter_fields)

			filter_fields = clean_fields(target.filter_fields, ",").split(",")
			values = clean_fields(target.fields_values, ",").split(",")
				
			if not empty_fields and not empty_values:
				if len(filter_fields) != len(values):
					frappe.throw(f"Mismatch: {len(filter_fields)} fields but {len(values)} values in row {target.idx}, DocType: {target.reference}.")