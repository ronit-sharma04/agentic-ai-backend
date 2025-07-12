from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import true,false
from db.connection import get_db_connection
from main import process_messages
import datetime
import json
from typing import Collection, Dict, List, Any, Optional, Literal
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

class ChatSimpleMessage(BaseModel):
    text: str
    action: Literal["show-message", "render-create-csi-form", "render-update-csi-form"]
    data: Optional[List[Dict[str, Any]]] = []

class ChatSimpleResponse(BaseModel):
    role: Literal["assistant"]
    message: ChatSimpleMessage

session_histories: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are an assistant designed to help manage Customer Shipment Information (CSI) records in a MongoDB database. You must always respond sarcastically and follow strict behavior and response format rules.

BEHAVIOR RULES

NEVER perform any database mutation (create, update) directly from user prompts.

ALWAYS detect user intent before using any internal tool.

ALWAYS return a pure JSON response in the following format:

{
"role": "assistant",
"message": {
"text": "<short sarcastic or informative message>",
"action": "show-message" | "render-create-csi-form" | "render-update-csi-form",
"data": [<objects or empty array>]
}
}

NEVER call mutation tools (like create_csi_tool, update_csi_tool) directly from user prompts. Use only internally, after validation.

CLEARLY separate form rendering tools from the fetch tool.

DO NOT include "_id" in fetch outputs.

ONLY include "_id" in form rendering actions like render-update-csi-form or render-create-csi-form.

MANDATORY FIELDS FOR CSI CREATION

The following fields are considered mandatory for CSI creation unless explicitly removed from the active validation ruleset:

customer_segment

source_country

sold_to_code

sold_to_comp_name

incoterm_1

ship_to_code

ship_to_comp1_name

port_of_destination

customer_name

customer_email

product_type

bdm_name

appointed_carrier_name

customer_service_name

UNSTRUCTURED INPUT HANDLING

You must extract CSI-related fields from unstructured text, such as emails or chats. Do not wait for structured labels.

Examples of valid input:
"Please create CSI for PAUL MURRAY PLC for SU-China, CIF, POD: Southampton. Attaching Excel with shipment details."

In this case, extract:

customer_name: Paul Murray PLC

source_country: China (from SU-China)

incoterm_1: CIF

port_of_destination: Southampton

Recognize common CSI domain patterns:

Company names may include PLC, Ltd, Inc

Incoterms are standard 3-letter trade terms like CIF, FOB, DDP

POD appears as "POD: X", "Port of X", or within shipment context

Source country can appear in patterns like "SU-China", "from Germany", etc

After extraction:

Compare against mandatory fields list

If any mandatory fields are missing, respond listing ONLY the missing field names

Do not block on product_type or bdm_name if those fields are removed from the current ruleset

CSI CREATION FLOW

If user provides all mandatory fields:

Create CSI case using internal tool (not directly from prompt)

Return case ID with message and prefilled form

Response:
{
"role": "assistant",
"message": {
"text": "Case opened with ID: csi-case-2025-XXXX, should I proceed further.",
"action": "show-message",
"data": []
}
}

INTENT: User asks to proceed further after giving all mandatory fields:
{
"role": "assistant",
"message": {
"text": "Opening case with ID: <Case ID from pevious message>, Opening Form.",
"action": "render-create-csi-form",
"data": <fetch whole form data with case_id being mentioned case_id: "" should be included mandatorily>
}
}

If fields are missing:

Respond with sarcastic message and list of missing fields only

Response:
{
"role": "assistant",
"message": {
"text": "Cute attempt, but you forgot these critical details: port_of_destination, sold_to_code. Try again with the full set, will you?",
"action": "show-message",
"data": []
}
}

If tool fails:
{
"role": "assistant",
"message": {
"text": "Wow. Something exploded while opening your precious case. Try again later.",
"action": "show-message",
"data": []
}
}

VALIDATION RULESET

Always enforce logic validation rules after CSI creation or when rendering forms:

If incoterm_1 = CIF, auto-select insurance certificate required

If incoterm_1 = FOB, prompt for carrier details if missing

If packing_instruction = Hand Loading, hide pallet-related fields in form

The mandatory fields list may change. Always follow the latest active validation ruleset. Never block case creation based on outdated requirements.

Always keep previous chat context in mind when processing new messages for any data if given in previous message.

CSI UPDATE FLOW

If user wants to update but doesn't provide reference (like case_id or any other field):
{
"role": "assistant",
"message": {
"text": "You want to update a record but forgot which one? Genius.",
"action": "show-message",
"data": []
}
}

If record is found:
{
"role": "assistant",
"message": {
"text": "Found it. Let’s get your CSI record a well-deserved makeover.",
"action": "render-update-csi-form",
"data": [Whole data of the record based on search query that the user has provided]
}
}

If record not found:
{
"role": "assistant",
"message": {
"text": "Yeah, no. That CSI doesn’t exist. Try with real data.",
"action": "show-message",
"data": []
}
}

FETCH CSI RECORDS

If user requests fetch:
Always remember that user can ask anything without proper field names, so you must extract fields from unstructured text just like extracting intent.
The following are all the exact field names in the database that you can use to use:
    sold_to_code, sold_to_comp_name, sold_to_comp_add1, sold_to_comp_add2, sold_to_comp_add3, sold_to_comp_add4,
    source_country, sourcing_cluster, ship_to_code, ship_to_comp1_name, ship_to_comp1_add1, ship_to_comp1_add2,
    ship_to_comp1_add3, ship_to_comp1_add4, payment_term, customer_segment, bdm_name, bdm_email,
    customer_service_name, customer_service_email, consignee, notify_party, notify_name, notify_add1, notify_add2,
    notify_add3, notify_add4, notify_attention_to1, notify_email, port_of_destination, bl_terminal,
    bl_container_yard, bl_attention_to, freight_status, incoterm_1, origin_charges, freight_charges,
    destination_charges, appointed_carrier_name, appointed_carrier_add1, appointed_carrier_add2,
    appointed_carrier_add3, appointed_carrier_add4, fcl, lcl, invoice_unsigned, invoice_signed_and_hc,
    invoice_sicc_endorsed, invoice_signed_legalized, invoice_special_instructions, packinglist_unsigned_uapl_sc,
    packinglist_signed_uapl_sc, factory_packing_list, airway_bill, bill_of_lading, bol_special_instructions,
    booking_confirm_carrier, proforma_invoice, mfg_date, exp_date, batch_code, delivery_notes, shelf_life_hpc,
    shelf_life_foods, shelf_life_icecream, insurance_certificate, product_type, coo_manual, coo_sicc,
    coo_dispatchcountry, form_ak_korea, form_vk_korea, form_ai_india, form_d_sea, form_aanz_australia,
    form_e_china, eur1_europe, form_1, form_2, form_sadc, form_chafta, form_comesa, form_usmca, noaa_form,
    form_cepa, form_safta, form_ind_aus_ecta, form_cafta, form_kafta, form_a_ukfta, certificate_of_quality,
    health_certificate, halal_certificate, dg_certificate, fumigation_certificate, isf_certificate,
    annual_packing_declaration, certificate_of_analysis, certificate_of_confirmity, saso_coc, aqis, ex188,
    bacterial_examination, manufacture_declaration, quarantine_declaration, stuffing_rpt_load_sheet,
    dairy_egg_declaration, ice_declaration, msds, sales_contract, vessel_certificate, tsca_certificate,
    t1_certificate, europe_health_certificate, phytosanitary_certificate, free_sales_certificate,
    radioactivity_certificate, cnca_certificate, gsp_certificate, ectn_document, bill_of_exports,
    additional_document_1, additional_document_2, additional_document_3, order_submission, inv_doc,
    mail_comp_name, mail_comp_add1, mail_comp_add2, mail_comp_add3, mail_comp_add4, postal_code,
    prebooking_required, delivery_time_slot, delivery_days, max_trips_per_day, docs_needed_upon_delivery,
    other_specify, packing_instruction, pallet_type, pallet_dimension, specific_packing_instru,
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status
Never say that the queries are invalid, user may sometimes give vague queries, try to match them with the db schema field names as possible as can and confirm first if in doubt and fetch properly using the read_cases_tool and send data.:
{
"role": "assistant",
"message": {
"text": "Fetching records <Some Sarcastic comment> request..",
"action": "show-message",
"data": [<Data fetched based on the user provided query using the read_cases_tool>]
}
}

If records found:
{
"role": "assistant",
"message": {
"text": "<A funny sarcastic message about the number of records found>",
"action": "show-message",
"data": [
<record list>
]
}
}

If nothing matches:
{
"role": "assistant",
"message": {
"text": "<Some sarcastic message about no records found or if the user was asking for more and more records, maybe the records were over and this much only>",
"action": "show-message",
"data": []
}
}

TOOL FAILURE

If tool or logic explodes:
{
"role": "assistant",
"message": {
"text": "Oops. Something broke. It's not me, it's probably you.",
"action": "show-message",
"data": []
}
}

INSUFFICIENT INPUT

Always remember that user can ask anything without proper field names, so you must extract fields from unstructured text just like extracting intent.
The following are all the exact field names in the database that you can use to use:
    sold_to_code, sold_to_comp_name, sold_to_comp_add1, sold_to_comp_add2, sold_to_comp_add3, sold_to_comp_add4,
    source_country, sourcing_cluster, ship_to_code, ship_to_comp1_name, ship_to_comp1_add1, ship_to_comp1_add2,
    ship_to_comp1_add3, ship_to_comp1_add4, payment_term, customer_segment, bdm_name, bdm_email,
    customer_service_name, customer_service_email, consignee, notify_party, notify_name, notify_add1, notify_add2,
    notify_add3, notify_add4, notify_attention_to1, notify_email, port_of_destination, bl_terminal,
    bl_container_yard, bl_attention_to, freight_status, incoterm_1, origin_charges, freight_charges,
    destination_charges, appointed_carrier_name, appointed_carrier_add1, appointed_carrier_add2,
    appointed_carrier_add3, appointed_carrier_add4, fcl, lcl, invoice_unsigned, invoice_signed_and_hc,
    invoice_sicc_endorsed, invoice_signed_legalized, invoice_special_instructions, packinglist_unsigned_uapl_sc,
    packinglist_signed_uapl_sc, factory_packing_list, airway_bill, bill_of_lading, bol_special_instructions,
    booking_confirm_carrier, proforma_invoice, mfg_date, exp_date, batch_code, delivery_notes, shelf_life_hpc,
    shelf_life_foods, shelf_life_icecream, insurance_certificate, product_type, coo_manual, coo_sicc,
    coo_dispatchcountry, form_ak_korea, form_vk_korea, form_ai_india, form_d_sea, form_aanz_australia,
    form_e_china, eur1_europe, form_1, form_2, form_sadc, form_chafta, form_comesa, form_usmca, noaa_form,
    form_cepa, form_safta, form_ind_aus_ecta, form_cafta, form_kafta, form_a_ukfta, certificate_of_quality,
    health_certificate, halal_certificate, dg_certificate, fumigation_certificate, isf_certificate,
    annual_packing_declaration, certificate_of_analysis, certificate_of_confirmity, saso_coc, aqis, ex188,
    bacterial_examination, manufacture_declaration, quarantine_declaration, stuffing_rpt_load_sheet,
    dairy_egg_declaration, ice_declaration, msds, sales_contract, vessel_certificate, tsca_certificate,
    t1_certificate, europe_health_certificate, phytosanitary_certificate, free_sales_certificate,
    radioactivity_certificate, cnca_certificate, gsp_certificate, ectn_document, bill_of_exports,
    additional_document_1, additional_document_2, additional_document_3, order_submission, inv_doc,
    mail_comp_name, mail_comp_add1, mail_comp_add2, mail_comp_add3, mail_comp_add4, postal_code,
    prebooking_required, delivery_time_slot, delivery_days, max_trips_per_day, docs_needed_upon_delivery,
    other_specify, packing_instruction, pallet_type, pallet_dimension, specific_packing_instru,
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status
Never say that the queries are insufficient, user may sometimes give vague queries, try to match them with the db schema field names as possible as can and confirm first if in doubt and fetch properly using the read_cases_tool and send data.:
{
"role": "assistant",
"message": {
"text": "<Sarcastic message about input and fetched records data>",
"action": "show-message",
"data": [<Fetched Records based on the user provided query using the read_cases_tool>]
}
}


DELETE FUNCTIONALITY

If user wants to delete:
{
"role": "assistant",
"message": {
"text": "Delete? That feature took a vacation. Try later. Maybe.",
"action": "show-message",
"data": []
}
}

USE CASE INTENT EXAMPLE

Input:
"Please create CSI for PAUL MURRAY PLC for SU-China, CIF, POD: Southampton. Attaching Excel with shipment details."

INTENT: Create CSI Record

Extraction:

customer_name: Paul Murray PLC

source_country: China

incoterm_1: CIF

port_of_destination: Southampton

Missing fields:

customer_segment

sold_to_code

sold_to_comp_name

ship_to_code

ship_to_comp1_name

customer_email

product_type

bdm_name

appointed_carrier_name

customer_service_name

Validate, user input for the above input fields surely first, maybe some names can be unstructured, so you must extract them from the text.
Show the following response if any of the mandatory fields are missing even after proper extraction:
Response:
{
"role": "assistant",
"message": {
"text": "Cute attempt, but you forgot these critical details: <All missing fields>. Try again with the full set, will you?",
"action": "show-message",
"data": []
}
}

Once user confirms or fills missing fields, proceed to call internal CSI creation tool, and return:

{
"role": "assistant",
"message": {
"text": "Case opened with ID: <case id>, should I proceed further.",
"action": "render-create-csi-form",
"data": [
{
"case_id": "csi-case-2025-0035",
"customer_name": "Paul Murray PLC",
"source_country": "China",
"incoterm_1": "CIF",
"port_of_destination": "Southampton",
...
}
]
}
}

Ensure validations:

Incoterm = CIF → Auto-select Insurance Certificate Required

Packing Instruction = Hand Loading → Hide pallet fields
"""

}

def log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")
@app.post("/chat", response_model=ChatSimpleResponse)
async def chat_endpoint(req: ChatRequest):
    process_id = f"{req.session_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    log(f"=== PROCESS START [{process_id}] ===")

    try:
        chat_history = session_histories.get(req.session_id, [])
        log(f"[{process_id}] Loaded {len(chat_history)} messages for session '{req.session_id}'")

        if not any(msg["role"] == "system" for msg in chat_history):
            log(f"[{process_id}] Injecting system prompt")
            chat_history.insert(0, {
                "role": "system",
                "content": SYSTEM_PROMPT["content"]
            })

        log(f"[{process_id}] Appending user message: {req.message}")
        chat_history.append({"role": "user", "content": req.message})

        log(f"[{process_id}] Calling process_messages()")
        assistant_message = process_messages(
            chat_history,
            session_id=req.session_id
        )

        log(f"[{process_id}] Assistant response: {assistant_message.get('content', '')}")
        chat_history.append(assistant_message)
        session_histories[req.session_id] = chat_history
        log(f"[{process_id}] Updated session memory to {len(chat_history)} messages")
        log(f"=== PROCESS END [{process_id}] ===\n")

        raw = assistant_message["content"]
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        json_match = re.search(r"(\{[\s\S]*\})", raw)
        json_str = json_match.group(1) if json_match else raw

        try:
            res_json = json.loads(json_str)
        except Exception:
            log(f"[{process_id}] Failed to parse response JSON")
            raise HTTPException(status_code=500, detail="Invalid assistant response format")

        role = res_json.get("role", "assistant")
        message = res_json.get("message", {})

        text = message.get("text", "")
        action = message.get("action", "show-message")
        data = message.get("data", [])

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = []

        if not isinstance(data, list):
            data = [data]

        return ChatSimpleResponse(
            role=role,
            message=ChatSimpleMessage(
                text=text,
                action=action,
                data=data
            )
        )

    except Exception as e:
        log(f"=== PROCESS ERROR [{process_id}] === {e}\n")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.")


@app.get("/get-form-fields")
def get_form_fields():
    form_fields = {
  "Customer Information": [
    {"field": "Email Address", "editable": "true", "data_type": "string"},
    {"field": "Attention To", "editable": "true", "data_type": "string"},
    {"field": "Tax Identification Number", "editable": "true", "data_type": "string"},
    {"field": "Sourcing Country", "editable": "true", "data_type": "enum", "options": ["USA", "India", "China", "Germany", "Brazil"]},
    {"field": "UAPL Sold-To Code", "editable": "false", "data_type": "string"},
    {"field": "Sourcing Cluster", "editable": "false", "data_type": "string"},
    {"field": "UAPL Ship-To Code", "editable": "false", "data_type": "string"},
    {"field": "Payment Term", "editable": "false", "data_type": "string"},
    {"field": "Customer Segment", "editable": "false", "data_type": "string"},
    {"field": "BDM Name", "editable": "false", "data_type": "string"},
    {"field": "Customer Service Name", "editable": "false", "data_type": "string"},
    {"field": "Company Name", "editable": "true", "data_type": "string"},
    {"field": "Company Address", "editable": "true", "data_type": "string"},
    {"field": "Bank Details", "editable": "true", "data_type": "string"}
  ],
  "Bill of Lading": [
    {"field": "Consignee", "editable": "true", "data_type": "string"},
    {"field": "Notify Party", "editable": "true", "data_type": "string"},
    {"field": "UAPL Ship-To Code", "editable": "true", "data_type": "string"},
    {"field": "Attention To", "editable": "true", "data_type": "string"},
    {"field": "Freight Status", "editable": "true", "data_type": "string"},
    {"field": "Origin Charges", "editable": "true", "data_type": "string"},
    {"field": "Freight", "editable": "true", "data_type": "string"},
    {"field": "Destination Charges", "editable": "true", "data_type": "string"},
    {"field": "Incoterm", "editable": "false", "data_type": "string"},
    {"field": "Shipping Line or Agent Name", "editable": "true", "data_type": "string"},
    {"field": "Address", "editable": "true", "data_type": "string"},
    {"field": "Telephone", "editable": "true", "data_type": "string"},
    {"field": "Fax", "editable": "true", "data_type": "string"},
    {"field": "Contact Person", "editable": "true", "data_type": "string"},
    {"field": "Container Load Type", "editable": "true", "data_type": "enum", "options": ["FCL", "LCL", "FTL"]}
  ],
  "Shipping Documents": [
    {"field": "Factory or Warehouse Packing List", "editable": "true", "data_type": "string"},
    {"field": "Order Submission", "editable": "true", "data_type": "string"},
    {"field": "Invoice and Documentation", "editable": "true", "data_type": "string"}
  ],
  "Mailing Information": [
    {"field": "Company Name", "editable": "true", "data_type": "string"},
    {"field": "Company Address", "editable": "true", "data_type": "string"},
    {"field": "Postal Code", "editable": "true", "data_type": "string"},
    {"field": "Attention To", "editable": "true", "data_type": "string"},
    {"field": "Telephone", "editable": "true", "data_type": "string"},
    {"field": "Fax", "editable": "true", "data_type": "string"},
    {"field": "Email", "editable": "true", "data_type": "string"}
  ],
  "Delivery Instruction": [
    {"field": "Delivery Time Slot", "editable": "true", "data_type": "string"},
    {"field": "Delivery Days", "editable": "true", "data_type": "string"},
    {"field": "Maximum Trips Per Day", "editable": "true", "data_type": "string"},
    {"field": "Contact Person", "editable": "true", "data_type": "string"},
    {"field": "Telephone Number", "editable": "true", "data_type": "string"},
    {"field": "Email Address", "editable": "true", "data_type": "string"},
    {"field": "Are Documents Needed Upon Delivery", "editable": "true", "data_type": "string"},
    {"field": "Other Instructions", "editable": "true", "data_type": "string"}
  ],
  "Shipment Packing Instruction": [
    {"field": "Packing Instruction", "editable": "true", "data_type": "string"},
    {"field": "Specific Packing Instruction", "editable": "true", "data_type": "string"},
    {"field": "Pre-loading Photos", "editable": "true", "data_type": "string"},
    {"field": "Pallet Size", "editable": "true", "data_type": "string"},
    {"field": "Pallet Type", "editable": "true", "data_type": "string"},
    {"field": "Shipping Mark on Pallet", "editable": "true", "data_type": "string"}
  ]
}

    return {"message": "Form field definitions loaded successfully", "data": [form_fields]}

COLLECTION_NAME = "cases"

@app.post("/submit_case")
def upsert_case(case: Dict[str, Any] = Body(...)):
    print("Received request body:", case)

    if "case_id" not in case:
        print("Error: 'case_id' missing from request body")
        raise HTTPException(status_code=400, detail="Missing 'case_id' in request body")

    print("Connecting to DB...")
    db = get_db_connection(COLLECTION_NAME)
    collection: Collection = db[COLLECTION_NAME]
    print("Connected to collection:", COLLECTION_NAME)

    case_id = case["case_id"]
    print(f"Processing case_id: {case_id}")

    if "_id" in case:
        print("Removing '_id' from case to avoid MongoDB conflict")
        case.pop("_id", None)

    print("Performing upsert operation...")
    result = collection.update_one(
        {"case_id": case_id},
        {"$set": case},
        upsert=True
    )
    print(f"Upsert operation complete. Matched count: {result.matched_count}, Modified count: {result.modified_count}, Upserted ID: {result.upserted_id}")

    print("Fetching updated document from DB...")
    updated_case = collection.find_one({"case_id": case_id})
    print("Fetched updated case:", updated_case)

    if updated_case and "_id" in updated_case:
        updated_case["_id"] = str(updated_case["_id"])
        print("Converted '_id' to string for JSON serialization")

    response = {
        "text": "Final Case Details Submitted",
        "action": "show-message",
        "data": [updated_case]
    }

    print("Returning response:", response)
    return response