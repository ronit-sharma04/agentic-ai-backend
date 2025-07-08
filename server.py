from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any
from main import process_messages
import datetime
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatSimpleResponse(BaseModel):
    message: str
    data: List[Dict[str, Any]]

# In-memory session store (volatile; resets when the app restarts)
session_histories: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content":    """
You are a helpful, conversational assistant that performs CRUD (Create, Read, Update, Delete) operations on a PostgreSQL table called 'csi' containing customer shipment information.

### SAFE BEHAVIOR RULES

- **DELETE**: Always perform a SELECT to verify the record exists before attempting deletion. If not found, respond that no matching record was found and no deletion was performed.
- **INSERT**: For inserting, if the user provides `csi_id` (the only mandatory field), you must proceed to create the record even if other fields are missing. Populate all other fields with empty string or null. First, check if a record with the same `csi_id` exists—if it does, skip insert and respond that the record already exists.
- **UPDATE**: Only proceed if the `csi_id` exists. Otherwise, return a message that the record was not found.
If any tool breaks or some random error is encountered, respond with a generic error message in the mentioned format itself and do not expose internal details.

### IF USER ASKS FOR AN ACTION WITHOUT PASSING DATA

If the user asks for help with an operation (e.g., “Can you insert something?” or “I want to delete a record”) but does not provide data:
- DO NOT respond with errors like “missing data.”
- DO respond positively and guide them by:
  - Acknowledging the request.
  - Asking for the required data.
  - Providing a detailed **markdown-formatted table** of all the fields the user can include.

### RESPONSE FORMAT

All your responses MUST follow this strict JSON format:

{
  "message": "<human-readable explanation>",
  "data": []
}

- **message**: Clearly explain what action was done or what’s needed.
- **data**:
  - For SELECT: return in the form of json for each row fetched. 
  - For CREATE/UPDATE/DELETE: return in the form of json for each row fetched. 
  - If no data is returned, use `[]`.
  - 
---

MONGODB COLLECTION SCHEMA: `csi`

```markdown
| Field Name                  | Type   | Required | Description                        |
|-----------------------------|--------|----------|------------------------------------|
| _id                         | string | YES      | Unique record ID                   |
| sold_to_code                | string | NO       |                                    |
| sold_to_comp_name           | string | NO       |                                    |
| sold_to_comp_add1           | string | NO       |                                    |
| sold_to_comp_add2           | string | NO       |                                    |
| sold_to_comp_add3           | string | NO       |                                    |
| sold_to_comp_add4           | string | NO       |                                    |
| source_country              | string | NO       |                                    |
| sourcing_cluster            | string | NO       |                                    |
| ship_to_code                | string | NO       |                                    |
| ship_to_comp1_name          | string | NO       |                                    |
| ship_to_comp1_add1          | string | NO       |                                    |
| ship_to_comp1_add2          | string | NO       |                                    |
| ship_to_comp1_add3          | string | NO       |                                    |
| ship_to_comp1_add4          | string | NO       |                                    |
| payment_term                | string | NO       |                                    |
| customer_segment            | string | NO       |                                    |
| bdm_name                    | string | NO       |                                    |
| bdm_email                   | string | NO       |                                    |
| customer_service_name       | string | NO       |                                    |
| customer_service_email      | string | NO       |                                    |
| consignee                   | string | NO       |                                    |
| notify_party                | string | NO       |                                    |
| notify_name                 | string | NO       |                                    |
| notify_add1                 | string | NO       |                                    |
| notify_add2                 | string | NO       |                                    |
| notify_add3                 | string | NO       |                                    |
| notify_add4                 | string | NO       |                                    |
| notify_attention_to1        | string | NO       |                                    |
| notify_email                | string | NO       |                                    |
| port_of_destination         | string | NO       |                                    |
| bl_terminal                 | string | NO       |                                    |
| bl_container_yard           | string | NO       |                                    |
| bl_attention_to             | string | NO       |                                    |
| freight_status              | string | NO       |                                    |
| incoterm_1                  | string | NO       |                                    |
| origin_charges              | string | NO       |                                    |
| freight_charges             | string | NO       |                                    |
| destination_charges         | string | NO       |                                    |
| appointed_carrier_name      | string | NO       |                                    |
| appointed_carrier_add1      | string | NO       |                                    |
| appointed_carrier_add2      | string | NO       |                                    |
| appointed_carrier_add3      | string | NO       |                                    |
| appointed_carrier_add4      | string | NO       |                                    |
| fcl                         | string | NO       |                                    |
| lcl                         | string | NO       |                                    |
| invoice_unsigned            | string | NO       |                                    |
| invoice_signed_and_hc       | string | NO       |                                    |
| invoice_sicc_endorsed       | string | NO       |                                    |
| invoice_signed_legalized    | string | NO       |                                    |
| invoice_special_instructions| string | NO       |                                    |
| packinglist_unsigned_uapl_sc| string | NO       |                                    |
| packinglist_signed_uapl_sc  | string | NO       |                                    |
| factory_packing_list        | string | NO       |                                    |
| airway_bill                 | string | NO       |                                    |
| bill_of_lading              | string | NO       |                                    |
| bol_special_instructions    | string | NO       |                                    |
| booking_confirm_carrier     | string | NO       |                                    |
| proforma_invoice            | string | NO       |                                    |
| mfg_date                    | string | NO       |                                    |
| exp_date                    | string | NO       |                                    |
| batch_code                  | string | NO       |                                    |
| delivery_notes              | string | NO       |                                    |
| shelf_life_hpc              | string | NO       |                                    |
| shelf_life_foods            | string | NO       |                                    |
| shelf_life_icecream         | string | NO       |                                    |
| insurance_certificate       | string | NO       |                                    |
| product_type                | string | NO       |                                    |
| coo_manual                  | string | NO       |                                    |
| coo_sicc                    | string | NO       |                                    |
| coo_dispatchcountry         | string | NO       |                                    |
| form_ak_korea               | string | NO       |                                    |
| form_vk_korea               | string | NO       |                                    |
| form_ai_india               | string | NO       |                                    |
| form_d_sea                  | string | NO       |                                    |
| form_aanz_australia         | string | NO       |                                    |
| form_e_china                | string | NO       |                                    |
| eur1_europe                 | string | NO       |                                    |
| form_1                      | string | NO       |                                    |
| form_2                      | string | NO       |                                    |
| form_sadc                   | string | NO       |                                    |
| form_chafta                 | string | NO       |                                    |
| form_comesa                 | string | NO       |                                    |
| form_usmca                  | string | NO       |                                    |
| noaa_form                   | string | NO       |                                    |
| form_cepa                   | string | NO       |                                    |
| form_safta                  | string | NO       |                                    |
| form_ind_aus_ecta           | string | NO       |                                    |
| form_cafta                  | string | NO       |                                    |
| form_kafta                  | string | NO       |                                    |
| form_a_ukfta                | string | NO       |                                    |
| certificate_of_quality      | string | NO       |                                    |
| health_certificate          | string | NO       |                                    |
| halal_certificate           | string | NO       |                                    |
| dg_certificate              | string | NO       |                                    |
| fumigation_certificate      | string | NO       |                                    |
| isf_certificate             | string | NO       |                                    |
| annual_packing_declaration  | string | NO       |                                    |
| certificate_of_analysis     | string | NO       |                                    |
| certificate_of_confirmity   | string | NO       |                                    |
| saso_coc                    | string | NO       |                                    |
| aqis                        | string | NO       |                                    |
| ex188                       | string | NO       |                                    |
| bacterial_examination       | string | NO       |                                    |
| manufacture_declaration     | string | NO       |                                    |
| quarantine_declaration      | string | NO       |                                    |
| stuffing_rpt_load_sheet     | string | NO       |                                    |
| dairy_egg_declaration       | string | NO       |                                    |
| ice_declaration             | string | NO       |                                    |
| msds                        | string | NO       |                                    |
| sales_contract              | string | NO       |                                    |
| vessel_certificate          | string | NO       |                                    |
| tsca_certificate            | string | NO       |                                    |
| t1_certificate              | string | NO       |                                    |
| europe_health_certificate   | string | NO       |                                    |
| phytosanitary_certificate   | string | NO       |                                    |
| free_sales_certificate      | string | NO       |                                    |
| radioactivity_certificate   | string | NO       |                                    |
| cnca_certificate            | string | NO       |                                    |
| gsp_certificate             | string | NO       |                                    |
| ectn_document               | string | NO       |                                    |
| bill_of_exports             | string | NO       |                                    |
| additional_document_1       | string | NO       |                                    |
| additional_document_2       | string | NO       |                                    |
| additional_document_3       | string | NO       |                                    |
| order_submission            | string | NO       |                                    |
| inv_doc                     | string | NO       |                                    |
| mail_comp_name              | string | NO       |                                    |
| mail_comp_add1              | string | NO       |                                    |
| mail_comp_add2              | string | NO       |                                    |
| mail_comp_add3              | string | NO       |                                    |
| mail_comp_add4              | string | NO       |                                    |
| postal_code                 | string | NO       |                                    |
| prebooking_required         | string | NO       |                                    |
| delivery_time_slot          | string | NO       |                                    |
| delivery_days               | string | NO       |                                    |
| max_trips_per_day           | string | NO       |                                    |
| docs_needed_upon_delivery   | string | NO       |                                    |
| other_specify               | string | NO       |                                    |
| packing_instruction         | string | NO       |                                    |
| pallet_type                 | string | NO       |                                    |
| pallet_dimension            | string | NO       |                                    |
| specific_packing_instru     | string | NO       |                                    |
| preloading_photos           | string | NO       |                                    |
| shipping_mark_on_pallet     | string | NO       |                                    |
| create_date                 | string | NO       |                                    |
| modify_date                 | string | NO       |                                    |
| csi_status                  | string | NO       |                                    |
```

Response Format:
    class ChatSimpleResponse(BaseModel):
      message: str
      data: List[Dict[str, Any]] 
keep this in mind always when responding to the user as this validation is done before sending back the response.

If a user does not provides any non mandatory fields, you must still create the record with empty data type as mentioned in the schema, for numeric put null if possible or zero.
You can suggest fields from this schema when asking the user for input.
Always guide them with a clear message and a field table they can use as a reference.
"""
}

def log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")
@app.post("/chat", response_model=ChatSimpleResponse)
async def chat_endpoint(req: ChatRequest):
    process_id = f"{req.session_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    log(f"=== PROCESS START [{process_id}] ===")
    try:
        # Load or initialize session history
        chat_history = session_histories.get(req.session_id, [])

        log(f"[{process_id}] Loaded {len(chat_history)} messages for session '{req.session_id}'")

        # Do NOT inject system prompt into chat_history anymore

        # Append the new user message
        log(f"[{process_id}] Appending user message: {req.message}")
        chat_history.append({"role": "user", "content": req.message})

        # Process message, pass system prompt separately
        log(f"[{process_id}] Calling LangGraph process_messages()")
        assistant_message = process_messages(
            chat_history,
            session_id=req.session_id,
            system_prompt=SYSTEM_PROMPT["content"]
        )
        log(f"[{process_id}] Assistant response: {assistant_message.get('content', '')}")
        chat_history.append(assistant_message)
        session_histories[req.session_id] = chat_history
        log(f"[{process_id}] Updated session memory to {len(chat_history)} messages")

        log(f"=== PROCESS END [{process_id}] ===\n")
        raw = assistant_message["content"]

        # Remove code block markers if present
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()

        # Try to extract a JSON object from anywhere in the string
        json_match = re.search(r"(\{[\s\S]*\})", raw)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw

        try:
            res_json = json.loads(json_str)
        except Exception:
            # fallback: just put the whole thing in message, empty data
            res_json = {"message": raw, "data": []}

        # Ensure 'data' is a list
        data = res_json.get("data", [])
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = []
        if not isinstance(data, list):
            data = [data]  # fallback: wrap in list

        message = res_json.get("message", "")
        return ChatSimpleResponse(message=message, data=data)

    except Exception as e:
        log(f"=== PROCESS ERROR [{process_id}] === {e}\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-form-fields")
def get_form_fields():
    form_fields = {
        "PART 1": {
            "Email Address": { "required": "true", "editable": "true", "data_type": "string" },
            "Attention To": { "required": "true", "editable": "true", "data_type": "string" },
            "Tax Identification Number": { "required": "true", "editable": "true", "data_type": "string" },
            "Sourcing Country": {
                "required": "true",
                "editable": "true",
                "data_type": "enum",
                "options": ["USA", "India", "China", "Germany", "Brazil"]
            },
            "Uapl Sold-To Code": { "required": "false", "editable": "false", "data_type": "string" },
            "Sourcing Cluster": { "required": "false", "editable": "false", "data_type": "string" },
            "Uapl Ship-To Code": { "required": "false", "editable": "false", "data_type": "string" },
            "Payment Term": { "required": "false", "editable": "false", "data_type": "string" },
            "Customer Segment": { "required": "false", "editable": "false", "data_type": "string" },
            "Bdm Name": { "required": "false", "editable": "false", "data_type": "string" },
            "Customer Service Name": { "required": "false", "editable": "false", "data_type": "string" },
            "Company Name": { "required": "false", "editable": "true", "data_type": "string" },
            "Company Address": { "required": "false", "editable": "true", "data_type": "string" },
            "Bank Details": { "required": "false", "editable": "true", "data_type": "string" }
        },
        "PART 2": {
            "Consignee": { "required": "true", "editable": "true", "data_type": "string" },
            "Notify Party": { "required": "true", "editable": "true", "data_type": "string" },
            "Uapl Ship-To  Code (Port Of Destination / Delivery Location Name)": { "required": "true", "editable": "true", "data_type": "string" },
            "(Attention To)": { "required": "true", "editable": "true", "data_type": "string" },
            "Freight Status": { "required": "false", "editable": "true", "data_type": "string" },
            "Origin Charges": { "required": "false", "editable": "true", "data_type": "string" },
            "Freight": { "required": "false", "editable": "true", "data_type": "string" },
            "Destination Charges": { "required": "false", "editable": "true", "data_type": "string" },
            "Incoterm": { "required": "false", "editable": "false", "data_type": "string" },
            "Shipping Line / Agent Name": { "required": "false", "editable": "true", "data_type": "string" },
            "Address": { "required": "false", "editable": "true", "data_type": "string" },
            "Telephone": { "required": "false", "editable": "true", "data_type": "string" },
            "Fax": { "required": "false", "editable": "true", "data_type": "string" },
            "Attention To": { "required": "false", "editable": "true", "data_type": "string" },
            "Container Load Type (Fcl ,Lcl ,Ftl)": { "required": "false", "editable": "true", "data_type": "string" }
        },
        "PART 3": {
            "Factory Packing List / Warehouse Packing List": { "required": "true", "editable": "true", "data_type": "string" },
            "Order Submission": { "required": "false", "editable": "true", "data_type": "string" },
            "Invoice & Documentation": { "required": "false", "editable": "true", "data_type": "string" },
            "Baki Sare .....................": { "required": "false", "editable": "true", "data_type": "string" }
        },
        "PART 4": {
            "Company Name": { "required": "false", "editable": "true", "data_type": "string" },
            "Company Address": { "required": "false", "editable": "true", "data_type": "string" },
            "Postal Code": { "required": "false", "editable": "true", "data_type": "string" },
            "Attention To": { "required": "false", "editable": "true", "data_type": "string" },
            "Telephone": { "required": "false", "editable": "true", "data_type": "string" },
            "Fax": { "required": "false", "editable": "true", "data_type": "string" },
            "Email": { "required": "false", "editable": "true", "data_type": "string" }
        },
        "PART 5": {
            "Delivery Time Slot": { "required": "false", "editable": "true", "data_type": "string" },
            "Delivery Day(s)": { "required": "false", "editable": "true", "data_type": "string" },
            "Maximum Trips Per Day": { "required": "false", "editable": "true", "data_type": "string" },
            "Contact Person": { "required": "false", "editable": "true", "data_type": "string" },
            "Telephone Number": { "required": "false", "editable": "true", "data_type": "string" },
            "Email Address": { "required": "false", "editable": "true", "data_type": "string" },
            "Are Documents Needed Upon Delivery?": { "required": "false", "editable": "true", "data_type": "string" },
            "Others, Specify": { "required": "false", "editable": "true", "data_type": "string" }
        },
        "PART 6": {
            "Packing Instruction": { "required": "true", "editable": "true", "data_type": "string" },
            "Specific Packing Instruction": { "required": "true", "editable": "true", "data_type": "string" },
            "Pre Loading Photos": { "required": "true", "editable": "true", "data_type": "string" },
            "Pallet Size": { "required": "false", "editable": "true", "data_type": "string" },
            "Pallet Type": { "required": "false", "editable": "true", "data_type": "string" },
            "Shipping Mark On Pallet (Name)": { "required": "false", "editable": "true", "data_type": "string" }
        }
    }

    return {"message": "Form field definitions loaded successfully", "data": [form_fields]}