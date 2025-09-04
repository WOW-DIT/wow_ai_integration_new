# Copyright (c) 2025, yazan sorour and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class AiSiteInformationManagement(Document):
	pass
@frappe.whitelist(allow_guest=True)
def create_site_info(
	action,
	employee_phone_number,
	license_number,
	site_owner,
	developer,
	engineering_design_office,
	site_id=None,
):
	doc = frappe.new_doc("Ai Site Information Management")

	doc.license_number = license_number
	doc.site_owner = site_owner
	doc.developer = developer
	doc.engineering_design_office = engineering_design_office
	doc.insert(ignore_permissions=True)
	frappe.db.commit()