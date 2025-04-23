import frappe
import requests
import json

@frappe.whitelist()
def get_models():
    settings = frappe.get_doc("Ai Settings", "Ai Settings")
    url = f"{settings.base_url}/tags"

    response = requests.get(url)

    if response.status_code == 200:
        models = []
        for m in response.json()["models"]:
            models.append({"model": m["model"]})

        return models

    frappe.throw("Couldn't fetch LLMs")


@frappe.whitelist()
def ai_chat(model, chat_id, new_message, stream=False):
    try:
        new_message = json.loads(new_message)

        chat = frappe.get_doc("Ai Chat", chat_id)
        
        message = frappe.new_doc("Ai Message")
        message.role = new_message["role"]
        message.content = new_message["content"]
        message.insert()

        chat.append(
            "messages", 
            {"message": message.name}
        )
        chat.save()

        messages = get_current_messages(chat_id)
        messages.append(new_message)

        settings = frappe.get_doc("Ai Settings", "Ai Settings")
        url = f"{settings.base_url}/chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            res_message = response.json()["message"]

            message = frappe.new_doc("Ai Message")
            message.role = res_message["role"]
            message.content = res_message["content"]
            message.insert()

            chat.append(
                "messages", 
                {"message": message.name}
            )
            chat.save()
            frappe.db.commit()

            return res_message["content"]
        else:
            frappe.throw("ERROR: response failed")

    except Exception as e:
        frappe.throw(f"Error: {e}")

@frappe.whitelist()
def get_current_messages(chat_id) -> list:
    messageDocs = frappe.get_all("Ai Messages Table", filters={"parent": chat_id}, fields=["role", "content"], order_by="idx")
    messages = []

    for m in messageDocs:
        messages.append({
            "role": m["role"],
            "content": m["content"]
        })
    
    return messages

@frappe.whitelist()
def getAIResponse(mctName, docName):
    """
    Generate a response from OpenAI's chat model based on a message context template and a target document.

    This function retrieves a message context template and the relevant target document from Frappe.
    It formats the text according to the specified fields and sends a prompt to the OpenAI API 
    to generate a response based on the provided system prompt and user prompt.

    Parameters:
        mctName (str): The name of the Message Context Template from which to retrieve formatting and prompts.
        docName (str): The name of the target document from which to retrieve field values.

    Returns:
        str: The content of the AI-generated response.

    Raises:
        frappe.ValidationError: If there is an issue with account credentials while calling the OpenAI API.
    """
    mctDoc = frappe.get_doc('Message Context Template', mctName)
    targetDocument = frappe.get_doc(mctDoc.target_doctype, docName)

    formattedText = ''

    for row in mctDoc.text_format:
        ## Concat table row fields
        if row.linked_field_type == "Table":
            msg = (row.before if row.before is not None else "")
            formattedText += msg + '\n'

            # doct = frappe.get_doc("DocType", row.target_doctype)
            row_children = frappe.get_all(
                "RAG Children Table",
                filters={"parent": mctDoc.name, "reference_type": row.target_doctype},
                fields=["content"],
            )

            for i, child in enumerate(row_children):
                child_fields = str(child.content).split(",")
                table_items = getattr(targetDocument, row.linked_field_name)

                for ti in table_items:

                    content = ""
                    for f in child_fields:
                        content += f". {getattr(ti, f)}"

                    ch_row = f"{i}- {content}"
                    formattedText += ch_row + '\n'

        else:
            msg = (row.before if row.before is not None else "") + " " + str(getattr(targetDocument, row.field_name)) + " " + (row.after if row.after is not None else "")
            formattedText += msg + '\n'

    """
    Search for records by selected references
    """
    for target in mctDoc.reference_targets:
        alias = "fi"
        sql_fields = ", ".join(f"{alias}.{field.strip()}" for field in target.fields.split(","))
        columns = "row_number|" + "|".join(f"{alias}.{field.strip()}" for field in target.fields.split(","))

        formattedText += f"{target.before}\n"
        formattedText += f"{target.reference} columns: {columns.replace(f'{alias}.', '')}\n"
        formattedText += f"{target.reference} rows:\n"

        if target.filter_fields != "" and target.filter_fields is not None and len(target.filter_fields.split(",")) > 0 and len(target.filter_fields.split(",")) == len(target.fields_values.split(",")):
            filter_fields = target.filter_fields.split(",")
            values = target.fields_values.split(",")
            sql_filters = []
            
            for i, f in enumerate(filter_fields):
                field = filter_fields[i].strip()
                value = values[i].strip()

                sql_filters.append(f"{alias}.{field} LIKE '%{value}%'")

            sql_filters = ", ".join(sql_filters)
            sql_filters = f"""WHERE {sql_filters}"""
        else:
            sql_filters = ""

        query = f"""
            SELECT {sql_fields}
            FROM `tab{target.reference}` AS {alias} {sql_filters};
        """

        target_items = frappe.db.sql(query, as_dict=True)

        for i, item in enumerate(target_items):
            item_row = f"{i+1}|{'|'.join(str(value) for value in item.values())}\n"

            formattedText += item_row

        formattedText += "\n"

    formattedText += '\n' + mctDoc.user_prompt

    # return formattedText
    # baseUrl = clientCredentials.base_url
    # apiUrl = clientCredentials.api_key
    systemPrompt = mctDoc.system_prompt
    userPrompt = formattedText

    # return userPrompt

    try:
        settings = frappe.get_doc("Ai Settings", "Ai Settings")
        url = f"{settings.base_url}/chat"
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPrompt}
        ]
        data = {
            "model": mctDoc.selected_model,
            "messages": messages,
            "stream": False,
        }
        response = requests.post(url, json=data)

        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            frappe.throw("ERROR: response failed")

    except Exception as e:
        frappe.throw(f"Error: {e}")
