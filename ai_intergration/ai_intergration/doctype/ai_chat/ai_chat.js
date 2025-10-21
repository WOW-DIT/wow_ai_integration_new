// Copyright (c) 2025, yazan sorour and contributors
// For license information, please see license.txt

frappe.ui.form.on('Ai Chat', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
			frm.add_custom_button("Go Live", () => {
				startLiveSession(frm);
			}).addClass("btn-primary");

			frm.add_custom_button("Clear Chat", () => {
				clearChat(frm);
			}).addClass("btn-primary");
		}

	},
	model: function(frm) {
		if(frm.doc.model) {
			frm.set_value("selected_model", frm.doc.model)
			frm.save()
		}
	},
	send: function(frm) {
		if(frm.doc.prompt && frm.doc.model){
			frappe.call({
				method: "ai_intergration.ai_intergration.api.ai_chat",
				args: {
					model: frm.doc.model,
					chat_id:frm.doc.name,
					new_message: {
						role: "user",
						content: frm.doc.prompt,
					}
				},
				callback: function(r) {
					console.log(r)
					frm.set_value('response', r.message);
				}
			})
		} else {
			if(!frm.doc.prompt) {
				frappe.throw("You can't send empty message");
			} else {
				frappe.throw("Please select a model.");
			}
		}
	}
});


function startLiveSession(frm) {
	let method = "";
	if(frm.doc.channel_type === "WhatsApp") {
		method = "whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.start_live_session"
	}
	else if(frm.doc.channel_type === "Instagram") {
		method = "instagram_integration.instagram.doctype.instagram_live_chat.instagram_live_chat.start_live_session"
	}
	else if(frm.doc.channel_type === "Facebook") {
		method = "whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.start_live_session"
	}
	frappe.call({
		method: method,
		args: {
			chat_id: frm.doc.name
		},
		callback: function(r) {
			if(r.message.success) {
				location.href = r.message.url;
			}
		}
	})
}


function clearChat(frm) {
	const d = new frappe.ui.Dialog({
        title: __(`Are you sure you want to clear chat. All Messages will be removed permanently.`),
        primary_action_label: __('Clear'),
        primary_action(values) {
            d.get_primary_btn().prop('disabled', true);
            frappe.call({
                method: `ai_intergration.ai_intergration.doctype.ai_chat.ai_chat.clear_chat`,
				args: {
					"chat_id": frm.doc.name
				},
                freeze: true,
                freeze_message: __('Deleting all messages...'),
                callback: function(res) {
                    if(res.message.success) {
                        frappe.msgprint(res.message.message)
                        reload_page();
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            })
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}


function getModels(frm) {
	frappe.call({
		method: "ai_intergration.ai_intergration.api.get_models",
		callback: function(r) {
			const models = [""];
			let selected_model = ""

			for(const m of r.message) {
				models.push(m.model)
				if(frm.doc.selected_model == m.model) {
					selected_model = m.model
				}
			}

			const model = frm.fields_dict['model'];

			frm.set_df_property("model", "options", models.join("\n"));
			
			if(selected_model) {
				frm.set_value('model', selected_model);
			} else {
				frm.refresh_field('model');
			}
		}
	})
}


function reload_page(){
    setTimeout(() => {
        location.reload();
    }, 3000);
}