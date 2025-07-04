from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any
from main import process_messages
import datetime
import json

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
    data: List[Dict[str, Any]]  # Changed to List[Dict] for better structure

# In-memory session store (volatile; resets when the app restarts)
session_histories: Dict[str, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = {
  "role": "system",
  "content": """
You are a helpful, conversational assistant that performs CRUD (Create, Read, Update, Delete) operations on a PostgreSQL table called 'csi' containing customer shipment information.

### SAFE BEHAVIOR RULES

- **DELETE**: Always perform a SELECT to verify the record exists before attempting deletion. If not found, respond that no matching record was found and no deletion was performed.
- **INSERT**: Always check if the provided `csi_id` already exists. If it does, return a message saying that the record already exists and skip the insert.
- **UPDATE**: Only proceed if the `csi_id` exists. Otherwise, return a message that the record was not found.

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
  "data": "<result data in markdown format in strict array of JSONs>" 
}

- **message**: Clearly explain what action was done or what’s needed.
- **data**:
  - For SELECT: return in the form of json for each row fetched. 
  - For CREATE/UPDATE/DELETE: return in the form of json for each row fetched. 
  - If no data is returned, use `[]`.

---

### TABLE SCHEMA: `public.csi`

```markdown
| Column Name                          | Type     | Nullable |
|-------------------------------------|----------|----------|
| csi_id                              | text     | NO       |
| sold_to_code                        | text     | YES      |
| sold_to_name                        | text     | YES      |
| sold_to_address_1                   | text     | YES      |
| sold_to_address_2                   | text     | YES      |
| sold_to_address_3                   | text     | YES      |
| sold_to_address_4                   | text     | YES      |
| source_country                      | text     | YES      |
| source_country_code                 | text     | YES      |
| sourcing_cluster                    | text     | YES      |
| ship_to_code                        | text     | YES      |
| ship_to_name                        | text     | YES      |
| ship_to_address_1                   | text     | YES      |
| ship_to_address_2                   | text     | YES      |
| ship_to_address_3                   | text     | YES      |
| ship_to_address_4                   | text     | YES      |
| ship_to_country_code                | text     | YES      |
| product_type                        | text     | YES      |
| payment_term                        | text     | YES      |
| kpi_l1                              | text     | YES      |
| kpi_l2                              | text     | YES      |
| kpi_l3                              | text     | YES      |
| bdm_name                            | text     | YES      |
| bdm_email                           | text     | YES      |
| abdm_name                           | text     | YES      |
| abdm_email                          | text     | YES      |
| customer_service_1_name            | text     | YES      |
| customer_service_1_email           | text     | YES      |
| customer_service_2_name            | text     | YES      |
| customer_service_2_email           | text     | YES      |
| customer_service_3_name            | text     | YES      |
| customer_service_3_email           | text     | YES      |
| customer_service_strategy          | text     | YES      |
| consignee                           | text     | YES      |
| notify_party                        | text     | YES      |
| notify_name                         | text     | YES      |
| notify_address_1                    | text     | YES      |
| notify_address_2                    | text     | YES      |
| notify_address_3                    | text     | YES      |
| notify_address_4                    | text     | YES      |
| notify_attention_to1               | text     | YES      |
| notify_email                        | text     | YES      |
| one_bl_per_container               | text     | YES      |
| bl_terminal                         | text     | YES      |
| bl_container_yard                   | text     | YES      |
| bl_attention_to                     | text     | YES      |
| freight_status                      | text     | YES      |
| incoterm_code                       | text     | YES      |
| incoterm_description                | text     | YES      |
| origin_charges                      | text     | YES      |
| freight_charges                     | text     | YES      |
| destination_charges                | text     | YES      |
| appointed_carrier_name             | text     | YES      |
| appointed_carrier_add1             | text     | YES      |
| appointed_carrier_add2             | text     | YES      |
| appointed_carrier_add3             | text     | YES      |
| appointed_carrier_add4             | text     | YES      |
| fcl                                 | text     | YES      |
| lcl                                 | text     | YES      |
| ftl                                 | text     | YES      |
| order_submission_email             | text     | YES      |
| inv_doc_email                       | text     | YES      |
| mail_comp_name                      | text     | YES      |
| mail_comp_address_1                | text     | YES      |
| mail_comp_address_2                | text     | YES      |
| mail_comp_add3                      | text     | YES      |
| mail_comp_add4                      | text     | YES      |
| postal_code                         | text     | YES      |
| prebooking_required                | text     | YES      |
| delivery_time_slot                 | text     | YES      |
| delivery_days                       | text     | YES      |
| max_trips_per_day                  | text     | YES      |
| docs_needed_upon_delivery         | text     | YES      |
| other_specify                       | text     | YES      |
| packing_instruction                | text     | YES      |
| pallet_type_or_size               | text     | YES      |
| specific_packing_instructions     | text     | YES      |
| preloading_photos                  | text     | YES      |
| shipping_mark_on_pallet           | text     | YES      |
| create_date                         | text     | YES      |
| modify_date                         | text     | YES      |
| csi_status                          | text     | YES      |
| port_of_discharge                  | text     | YES      |
| port_of_discharge_code            | text     | YES      |
| shipment_type                      | text     | YES      |
| draft_bl_validated_by_customer    | text     | YES      |
| ui_data_source                      | text     | YES      |
| pallet_double_stacking_of_pallets_yn | text  | YES      |
| pallet_length_m                     | numeric  | YES      |
| pallet_width_m                      | numeric  | YES      |
| pallet_height_m                     | numeric  | YES      |
| pallet_double_stacking             | text     | YES      |
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

        if not chat_history:

            log(f"[{process_id}] No history found, injecting system prompt.")

            chat_history.append(SYSTEM_PROMPT)

        # Append the new user message
        log(f"[{process_id}] Appending user message: {req.message}")

        chat_history.append({"role": "user", "content": req.message})

        # Process message
        log(f"[{process_id}] Calling LangGraph process_messages()")

        assistant_message = process_messages(chat_history, session_id=req.session_id)

        log(f"[{process_id}] Assistant response: {assistant_message.get('content', '')}")

        chat_history.append(assistant_message)

        # Save updated chat history
        session_histories[req.session_id] = chat_history

        log(f"[{process_id}] Updated session memory to {len(chat_history)} messages")

        # import pdb
        # pdb.set_trace()  # Debugging breakpoint

        log(f"=== PROCESS END [{process_id}] ===\n")
        res = assistant_message["content"].replace("```", "").replace("json", "")
        res_json = json.loads(res)
        return ChatSimpleResponse(**res_json)

    except Exception as e:
        log(f"=== PROCESS ERROR [{process_id}] === {e}\n")
        raise HTTPException(status_code=500, detail=str(e))
