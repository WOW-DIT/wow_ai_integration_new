// Copyright (c) 2024, yazan sorour and contributors
// For license information, please see license.txt

var linkedDoctypes = {};

frappe.ui.form.on('Message Context Template', {
	 refresh: function(frm , cdt , cdn) {
		if(frm.doc.target_doctype != null && frm.doc.target_doctype != ''){
			getEventDoctypes(frm,cdt,cdn)
		}

		getModels(frm)


		let c = [{}]
	},
	llm: function(frm){
		if(frm.doc.llm) {
			frm.set_value("selected_model", frm.doc.llm)
		}
	},
	target_doctype: function (frm , cdt ,cdn){
		//var item = locals[cdt][cdn];
		getEventDoctypes(frm , cdt , cdn );
	}
	
});

function getEventDoctypes(frm,cdt,cdn)
{
    frappe.model.with_doctype(frm.doc.target_doctype, function() {
		console.log("AAAAAAA")
    	var options = $.map(frappe.get_meta(frm.doc.target_doctype).fields,
    			function(d) {
					
					if(d.fieldname) {							
						if (d.fieldtype == "Link" && d.options != "Workflow State") {
							linkedDoctypes[d.options] = {fieldname: d.fieldname, fieldtype: d.fieldtype};
							return d.options;
						}
		
						// For Table fields
						if (d.fieldtype == "Table") {
							linkedDoctypes[d.options] = {fieldname: d.fieldname, fieldtype: d.fieldtype};
							var childDoctype = d.options;
							if (childDoctype) {
								return childDoctype;
							}
						}
					}
    		  	}
    		);
            options.push(frm.doc.target_doctype);
            
            frm.fields_dict['text_format'].grid.get_field("target_doctype").get_query = function(doc, cdt, cdn) {
            	return {
            		filters: {
            		    "name":['in',options]
            		}
            	}
            }
    	});
}

frappe.ui.form.on('Text Format Table','target_doctype',function(frm,cdt,cdn){
	var item = locals[cdt][cdn];

	frappe.model.with_doctype(item.target_doctype, function() {
	var options = $.map(frappe.get_meta(item.target_doctype).fields,
			function(d) {
			if(d.fieldname && frappe.model.no_value_type.indexOf(d.fieldtype)===-1) {
			return d.fieldname;
				}
			return null;
			}
		);
		 
		frm.fields_dict.text_format.grid.update_docfield_property(
			'field_name',
			'options',
			[""].concat(options)
		);

		frm.fields_dict.text_format.grid.update_docfield_property(
			'field_name2',
			'options',
			[""].concat(options)
		);
		// console.log(item.target_doctype)
		// console.log(frm.doc.target_doctype)
		if(item.target_doctype != frm.doc.target_doctype){
			// debugger
			frappe.model.set_value(cdt, cdn, 'linked_field_name',
				linkedDoctypes[item.target_doctype].fieldname
			);
			frappe.model.set_value(cdt, cdn, 'linked_field_type',
				linkedDoctypes[item.target_doctype].fieldtype
			);
		}
	});
	
	frm.refresh_field("text_format");
 })



function loadFieldsFromTargetDoctype(frm){
	frappe.model.with_doctype(frm.doc.target_doctype, function() {
		var options = $.map(frappe.get_meta(frm.doc.target_doctype).fields,
				function(d) {
				if(d.fieldname && frappe.model.no_value_type.indexOf(d.fieldtype)===-1) {
				return d.fieldname;
					}
				return null;
				}
			);
				
			frm.fields_dict.text_format.grid.update_docfield_property(
				'field_name',
				'options',
				[""].concat(options)
				);

			frm.fields_dict.text_format.grid.update_docfield_property(
				'field_name2',
				'options',
				[""].concat(options)
				);
		});
   		frm.refresh_field("text_format");
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

			const model = frm.fields_dict['llm'];

			frm.set_df_property("llm", "options", models.join("\n"));
			
			if(selected_model) {
				frm.set_value('llm', selected_model);
			} else {
				frm.refresh_field('llm');
			}
		}
	})
}

/*
frappe.ui.form.on('HL7 Mapping Table','target_doctype',function(frm,cdt,cdn){
	var item = locals[cdt][cdn];
   frappe.model.with_doctype(item.target_doctype, function() {
   var options = $.map(frappe.get_meta(item.target_doctype).fields,
		   function(d) {
		   if(d.fieldname && frappe.model.no_value_type.indexOf(d.fieldtype)===-1) {
		   return d.fieldname;
			   }
		   return null;
		   }
	   );
		
	   frm.fields_dict.mapping_table.grid.update_docfield_property(
			   'value',
			   'options',
			   [""].concat(options)
			   );
   });
   
   frm.refresh_field("text_format");
})
*/
