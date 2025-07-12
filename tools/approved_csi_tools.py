from langchain_core.tools import tool
from crud.approved_csi_crud import find_in_approved_csi_collection
from pydantic import ValidationError
from tools.cases_args import CSIToolArgs
import logging


@tool
def read_approved_csi_tool(inputs: CSIToolArgs) -> dict:
    """
    Retrieve Approved CSI (Customer Shipment Instruction) records from the database using advanced filtering and pagination.

    This tool accepts multiple optional filtering parameters based on the Approved CSI schema and returns up to 5 records per page.

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
    preloading_photos, shipping_mark_on_pallet, create_date, modify_date, csi_status

    === Returns ===
    - A message with the total number of matching records and page info.
    - A list of up to 5 matched Approved CSI documents (with `_id` removed).

    Example Usage:
    Use this tool to search for Approved CSI records using any of the fields of the schema with exact name from schema and paginate through the results.
    """

    data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}
    print(f"[APPROVED CSI READ TOOL] Called with inputs={data}")
    result = find_in_approved_csi_collection(**data)
    print(f"[APPROVED CSI READ TOOL] Result: {result}")
    return result

read_approved_csi_tool.name = "approved_csi_read_tool"
