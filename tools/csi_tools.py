from langchain_core.tools import tool
from crud.cases_crud import create_cases, read_cases, approve_cases
from pydantic import ValidationError
from tools.cases_args import CSIToolArgs
import logging


@tool
def read_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Retrieve CSI (Customer Shipment Instruction) records from the database using advanced filtering and pagination.

    This tool accepts multiple optional filtering parameters based on the CSI schema and returns up to 5 records per page.

    === Capabilities ===
    - Supports full-text, case-insensitive search on string fields.
    - Accepts MongoDB ObjectId (`id` or `_id`) when provided.
    - Filters only non-empty fields automatically.
    - Paginates results using the `page` parameter (default: 1).
    - Returns a summary message and matched records.

    === Filterable Fields ===
    You can provide any of the following fields as filters:
    
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
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status, page

    === Returns ===
    - A message with the total number of matching records and page info.
    - A list of up to 5 matched CSI documents (with `_id` removed).

    Example Usage:
    Use this tool to search for CSI cases using any of the fields of the schema with exact name from scehma and paginate through the results.
    """

    data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}
    print(f"[CSI READ TOOL] Called with inputs={data}")
    result = read_cases(**data)
    print(f"[CSI READ TOOL] Result: {result}")
    return result

read_cases_tool.name = "csi_read_tool"


@tool
def create_cases_tool(inputs: CSIToolArgs) -> str:
    """
    Create a new CSI (Customer Shipment Instruction) record in the database using provided input fields.

    This tool accepts all CSI fields (as per the schema) and inserts a new record into the CSI database.

    === Capabilities ===
    - Accepts any combination of valid CSI fields as input.
    - Automatically generates a unique `case_id` for the record.
    - Sets default status `csi_status = "pending"` for every new record.
    - Excludes `_id` (MongoDB auto-generates it).
    - Validates data using Pydantic before database insertion.

    === Insertable Fields ===
    You can provide values for any of the following fields:
    
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
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status, page

    === Returns ===
    - A confirmation message like: `"Case opened with ID: csi-case-123456, should I proceed further."`
    - On error, returns one of:
        - `[CREATE ERROR] Validation error occurred.`
        - `[CREATE ERROR] Case with this case_id already exists.`
        - `[CREATE ERROR] An unexpected error occurred while creating the Case.`

    Example Usage:
    Use this tool to create a new CSI record by supplying relevant shipment instruction details. You do not need to provide `_id`, `case_id`, or `csi_status`—these are handled automatically.
    """
    try:
        data = inputs.model_dump()
        result = create_cases(**data)
        return result
    except ValidationError as e:
        logging.error("Validation error in create_csi_tool: %s", e)
        return "[CREATE ERROR] Validation error occurred."
    except Exception as e:
        logging.error("Error in create_csi_tool: %s", e)
        return "[CREATE ERROR] An unexpected error occurred."
create_cases_tool.name = "create_cases_tool"


@tool
def approve_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Approve CSI (Customer Shipment Instruction) records by updating their status and transferring them to the approved_csi collection.

    This tool filters CSI records based on provided input parameters, updates their `csi_status` to `"approved"`, and stores them into the `approved_csi` collection.

    === Capabilities ===
    - Filters records using flexible field matching (same as `read_cases_tool`).
    - Updates all matching CSI records with `csi_status = "approved"`.
    - Uploads the updated documents to the `approved_csi` collection.
    - Returns a message with the number of updated and uploaded records.

    === Updatable Fields (used for filtering) ===
    Use any of the valid CSI fields as filters to match the records that should be approved:
    
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
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status, page

    === Returns ===
    - A success message indicating how many cases were approved and moved.
    - A list of approved CSI documents (with `_id` removed).
    - In case of failure, returns an appropriate error message.

    Example Usage:
    Use this tool to bulk-approve CSI records that match any filtering criteria. All approved cases will be updated in the CSI collection and inserted into the `approved_csi` collection.
    """
    try:
        data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}
        print(f"[CSI APPROVE TOOL] Called with inputs={data}")
        result = approve_cases(**data)
        print(f"[CSI APPROVE TOOL] Result: {result}")
        return result
    except ValidationError as e:
        logging.error("Validation error in approve_cases_tool: %s", e)
        return {"error": True, "message": "[APPROVE ERROR] Validation error occurred."}
    except Exception as e:
        logging.error("Unexpected error in approve_cases_tool: %s", e)
        return {"error": True, "message": "[APPROVE ERROR] An unexpected error occurred."}


approve_cases_tool.name = "csi_approve_tool"

from langchain_core.tools import tool
from crud.cases_crud import update_case
from pydantic import ValidationError
from tools.cases_args import CSIToolArgs
import logging


@tool
def update_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Update CSI (Customer Shipment Instruction) records by specifying filter (query) fields 
    and fields to update separately.

    === Capabilities ===
    - Filter fields (`query_fields`) are used to locate a matching CSI record.
    - Update fields (`update_fields`) are used to change values in the matched record.
    - Fields used for filtering will NOT be updated.
    - Supports partial updates — only provide fields you wish to query or change.
    - Skips empty or null fields automatically.

    === Input Structure ===
    {
        "query_fields": { ... },   # Filters to locate the record
        "update_fields": { ... }   # Fields and values to update
    }

    === Filterable & Updatable Fields ===
    You can use any CSI field for both filtering and updating, including:
    sold_to_code, customer_segment, bdm_email, consignee, invoice_signed_legalized, etc.

    === Returns ===
    - `"Case updated successfully."` + the updated record.
    - `"No matching Case found. Update not performed."` if nothing matches.
    - `"No changes made to the Case."` if no actual update occurs.
    - `[UPDATE ERROR]` messages on exception.
    """

    try:
        query_fields = {
            k: v for k, v in inputs.get("query_fields", {}).items() if v not in ("", None)
        }
        update_fields = {
            k: v for k, v in inputs.get("update_fields", {}).items() if v not in ("", None)
        }

        if not query_fields or not update_fields:
            return {
                "error": True,
                "message": "Both 'query_fields' and 'update_fields' must be provided and non-empty."
            }

        print(f"[CSI UPDATE TOOL] Query: {query_fields}")
        print(f"[CSI UPDATE TOOL] Update: {update_fields}")
        result = update_case(query_fields=query_fields, update_fields=update_fields)
        print(f"[CSI UPDATE TOOL] Result: {result}")
        return result

    except ValidationError as e:
        logging.error("Validation error in update_cases_tool: %s", e)
        return {"error": True, "message": "[UPDATE ERROR] Validation error occurred."}
    except Exception as e:
        logging.error("Unexpected error in update_cases_tool: %s", e)
        return {"error": True, "message": "[UPDATE ERROR] An unexpected error occurred."}



@tool
def approve_cases_tool(inputs: CSIToolArgs) -> dict:
    """
    Approve CSI (Customer Shipment Instruction) records based on provided filters.

    This tool identifies CSI records using any combination of CSI fields and marks them as approved.
    Approved records are copied into a separate collection and their status is updated in the original collection.

    === Capabilities ===
    - Uses flexible filters to identify matching CSI records.
    - Adds approved records into the `approved_csi` collection (excluding `_id` to prevent duplication).
    - Updates the `csi_status` of matching records to `"approved"` in the original collection.
    - Handles ObjectId conversion when `_id` or `id` is provided.
    - Returns a message along with the approved records.

    === Filterable Fields ===
    You can use any field from the CSI schema as a filter, including but not limited to:

    sold_to_code, ship_to_code, source_country, customer_service_name, bdm_email, vessel_certificate, 
    invoice_signed_and_hc, bl_terminal, prebooking_required, csi_status, create_date, etc.

    === Returns ===
    - `"Approved X case(s)."` with list of approved cases.
    - `"No matching CSI Cases found to approve."` if no match found.
    - `[APPROVE ERROR]` messages on exception.

    Example Usage:
    Use this tool when you want to approve matching CSI records by providing relevant filter fields.
    """

    try:
        data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}
        print(f"[CSI APPROVE TOOL] Called with inputs={data}")
        result = approve_cases(**data)
        print(f"[CSI APPROVE TOOL] Result: {result}")
        return result
    except ValidationError as e:
        logging.error("Validation error in approve_cases_tool: %s", e)
        return {"error": True, "message": "[APPROVE ERROR] Validation error occurred."}
    except Exception as e:
        logging.error("Unexpected error in approve_cases_tool: %s", e)
        return {"error": True, "message": "[APPROVE ERROR] An unexpected error occurred."}


approve_cases_tool.name = "approve_cases_tool"
