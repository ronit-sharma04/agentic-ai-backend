from db.connection import get_db_connection
import pdb


def create_csi(row: dict) -> str:
    pdb.set_trace()
    print("[CREATE] Input row:", row)

    # Validate csi_id
    csi_id = row.get("csi_id")
    if not csi_id:
        print("[CREATE ERROR] Missing required field: csi_id")
        return '[CREATE ERROR] Missing required field: csi_id'

    # Define the full list of columns from the schema
    ALL_COLUMNS = [
        "csi_id", "sold_to_code", "sold_to_name", "sold_to_address_1", "sold_to_address_2", "sold_to_address_3",
        "sold_to_address_4", "source_country", "source_country_code", "sourcing_cluster", "ship_to_code",
        "ship_to_name", "ship_to_address_1", "ship_to_address_2", "ship_to_address_3", "ship_to_address_4",
        "ship_to_country_code", "product_type", "payment_term", "kpi_l1", "kpi_l2", "kpi_l3", "bdm_name",
        "bdm_email", "abdm_name", "abdm_email", "customer_service_1_name", "customer_service_1_email",
        "customer_service_2_name", "customer_service_2_email", "customer_service_3_name", "customer_service_3_email",
        "customer_service_strategy", "consignee", "notify_party", "notify_name", "notify_address_1",
        "notify_address_2", "notify_address_3", "notify_address_4", "notify_attention_to1", "notify_email",
        "one_bl_per_container", "bl_terminal", "bl_container_yard", "bl_attention_to", "freight_status",
        "incoterm_code", "incoterm_description", "origin_charges", "freight_charges", "destination_charges",
        "appointed_carrier_name", "appointed_carrier_add1", "appointed_carrier_add2", "appointed_carrier_add3",
        "appointed_carrier_add4", "fcl", "lcl", "ftl", "order_submission_email", "inv_doc_email", "mail_comp_name",
        "mail_comp_address_1", "mail_comp_address_2", "mail_comp_add3", "mail_comp_add4", "postal_code",
        "prebooking_required", "delivery_time_slot", "delivery_days", "max_trips_per_day", "docs_needed_upon_delivery",
        "other_specify", "packing_instruction", "pallet_type_or_size", "specific_packing_instructions",
        "preloading_photos", "shipping_mark_on_pallet", "create_date", "modify_date", "csi_status",
        "port_of_discharge", "port_of_discharge_code", "shipment_type", "draft_bl_validated_by_customer",
        "ui_data_source", "pallet_double_stacking_of_pallets_yn", "pallet_length_m", "pallet_width_m",
        "pallet_height_m", "pallet_double_stacking"
    ]

    # Ensure all fields are present: use provided values or default to ""
    full_row = {col: row.get(col, "") for col in ALL_COLUMNS}

    # Build the insert query
    placeholders = ', '.join(['%s'] * len(ALL_COLUMNS))
    sql = f"INSERT INTO csi ({', '.join(ALL_COLUMNS)}) VALUES ({placeholders}) RETURNING csi_id;"
    vals = [full_row[col] for col in ALL_COLUMNS]

    print("[CREATE] SQL:", sql)
    print("[CREATE] Values:", vals)

    # Execute query
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, vals)
        new_id = cur.fetchone()[0]
        conn.commit()
        print("[CREATE] Inserted csi_id:", new_id)
        return f"CSI row created with csi_id: {new_id}"
    except Exception as e:
        conn.rollback()
        print("[CREATE ERROR]", e)
        return f"[CREATE ERROR] {e}"
    finally:
        cur.close()
        conn.close()
        print("[CREATE] Connection closed.")

def read_csi(csi_id: str = None, sold_to_name: str = None) -> str:
    print("[READ] Params - csi_id:", csi_id, ", sold_to_name:", sold_to_name)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if csi_id:
            sql = "SELECT * FROM csi WHERE csi_id = %s;"
            print("[READ] SQL:", sql)
            cur.execute(sql, (csi_id,))
        elif sold_to_name:
            sql = "SELECT * FROM csi WHERE sold_to_name ILIKE %s;"
            print("[READ] SQL:", sql)
            cur.execute(sql, (f"%{sold_to_name}%",))
        else:
            sql = "SELECT * FROM csi LIMIT 50;"
            print("[READ] SQL:", sql)
            cur.execute(sql)

        rows = cur.fetchall()
        if not rows:
            print("[READ] No records found.")
            return "No CSI records found."

        columns = [desc[0] for desc in cur.description]
        print("[READ] Columns:", columns)
        return "\n---\n".join([
            ', '.join(f"{col}: {val}" for col, val in zip(columns, row)) for row in rows
        ])
    except Exception as e:
        print("[READ ERROR]", e)
        return f"[READ ERROR] {e}"
    finally:
        cur.close()
        conn.close()
        print("[READ] Connection closed.")

def update_csi(csi_id: str, updates: dict) -> str:
    print("[UPDATE] csi_id:", csi_id)
    print("[UPDATE] Updates before filtering:", updates)

    updates = {k: v for k, v in updates.items() if k != 'csi_id'}
    print("[UPDATE] Valid updates:", updates)

    if not updates:
        print("[UPDATE ERROR] No valid fields to update.")
        return "[UPDATE ERROR] No valid fields to update."

    set_clause = ', '.join([f"{k} = %s" for k in updates])
    values = list(updates.values()) + [csi_id]
    sql = f"UPDATE csi SET {set_clause} WHERE csi_id = %s;"
    print("[UPDATE] SQL:", sql)
    print("[UPDATE] Values:", values)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, values)
        conn.commit()
        if cur.rowcount:
            print("[UPDATE] Record updated.")
            return "CSI record updated successfully."
        else:
            print("[UPDATE] No record found.")
            return f"No CSI record found with csi_id {csi_id}."
    except Exception as e:
        conn.rollback()
        print("[UPDATE ERROR]", e)
        return f"[UPDATE ERROR] {e}"
    finally:
        cur.close()
        conn.close()
        print("[UPDATE] Connection closed.")

def delete_csi(csi_id: str) -> str:
    print("[DELETE] csi_id:", csi_id)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM csi WHERE csi_id = %s RETURNING csi_id;", (csi_id,))
        deleted = cur.fetchone()
        conn.commit()
        if deleted:
            print("[DELETE] Deleted csi_id:", deleted[0])
            return f"CSI record with csi_id {csi_id} deleted successfully."
        else:
            print("[DELETE] No record found.")
            return f"No CSI record found with csi_id {csi_id}."
    except Exception as e:
        conn.rollback()
        print("[DELETE ERROR]", e)
        return f"[DELETE ERROR] {e}"
    finally:
        cur.close()
        conn.close()
        print("[DELETE] Connection closed.")

def bulk_delete_csi(**criteria) -> str:
    print("[BULK DELETE] Input criteria:", criteria)

    if not criteria:
        print("[BULK DELETE] No conditions provided.")
        return "No conditions provided for bulk delete."

    allowed = set([...])  # Truncated for readability
    for k in list(criteria):
        if k not in allowed:
            print(f"[BULK DELETE] Removing invalid key: {k}")
            criteria.pop(k)

    if not criteria:
        print("[BULK DELETE] No valid conditions after filtering.")
        return "No valid conditions for bulk delete."

    where_clause = " AND ".join([f"{k} = %s" for k in criteria])
    params = [v for v in criteria.values()]
    print("[BULK DELETE] SQL WHERE clause:", where_clause)
    print("[BULK DELETE] Params:", params)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT csi_id FROM csi WHERE {where_clause};", params)
        to_delete = [r[0] for r in cur.fetchall()]
        print("[BULK DELETE] Matching records:", to_delete)

        if not to_delete:
            print("[BULK DELETE] No records to delete.")
            return "No CSI records matched the given conditions."

        cur.execute(f"DELETE FROM csi WHERE {where_clause};", params)
        conn.commit()
        print("[BULK DELETE] Deleted records:", to_delete)
        return f"Deleted csi_id(s): {', '.join(to_delete)}"
    except Exception as e:
        conn.rollback()
        print("[BULK DELETE ERROR]", e)
        return f"[BULK DELETE ERROR] {e}"
    finally:
        cur.close()
        conn.close()
        print("[BULK DELETE] Connection closed.")
