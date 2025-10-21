# Copyright (c) 2025, yazan sorour and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class AiChat(Document):
	pass


@frappe.whitelist()
def clear_chat(chat_id):
	try:
		chat = frappe.get_doc("Ai Chat", chat_id)

		frappe.set_value("Ai Chat", chat.name, "messages", [])

		channel_type = chat.channel_type
		if channel_type == "WhatsApp":
			filters = {
				"chat": chat.name,
				"channel_type": chat.channel_type,
				"whatsapp_instance": chat.whatsapp_instance,
			}
		elif channel_type == "Instagram":
			filters = {
				"chat": chat.name,
				"channel_type": chat.channel_type,
				"instagram_instance": chat.instagram_instance,
			}

		messages = frappe.get_list(
			"Ai Message",
			filters=filters,
			limit=0,
		)

		deleted_messages = 0
		for msg in messages:
			frappe.delete_doc_if_exists (
				"Ai Message",
				msg.name,
				force=1,
			)
			deleted_messages += 1

		return {"success": True, "message": f"{_("Chat cleared successfully. Number of deleted messages")} ({deleted_messages})."}

	except Exception as e:
		return {"success": False, "error": str(e)}
