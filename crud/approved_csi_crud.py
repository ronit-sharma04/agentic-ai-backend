from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random
import datetime
import traceback

COLLECTION = "approved_csi"

def read_approved_csi(page: int = 1, **kwargs) -> dict:
    """
    Read approved CSI records from the database based on provided filters.
    
    Args:
        page: Page number for pagination
        **kwargs: Filter parameters (field_name=value pairs)
        
    Returns:
        dict: Contains message and data with matched records
    """
    print(f"[APPROVED_CSI READ] Called with kwargs={kwargs}, page={page}")
    try:
        db = get_db_connection(COLLECTION)
        print("[APPROVED_CSI READ] Got DB connection")
        coll = db[COLLECTION]

        # Build query
        query = {}
        sort_params = kwargs.pop('sort', None)
        limit_param = kwargs.pop('limit', None)
        
        for k, v in kwargs.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        query["_id"] = ObjectId(v)
                    except Exception:
                        query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    query[k] = v

        print("[APPROVED_CSI READ] Query:", query)

        total_count = coll.count_documents(query)
        print(f"[APPROVED_CSI READ] Total matching records: {total_count}")
        if total_count == 0:
            return {"status": "success", "message": "No Approved CSI Records found.", "data": []}

        # Use provided limit or default to pagination limit
        if limit_param:
            limit = int(limit_param)
        else:
            limit = 5
        
        offset = (page - 1) * limit
        
        # Apply sorting if provided
        if sort_params:
            cursor = coll.find(query, {"_id": 0}).sort(sort_params).skip(offset).limit(limit)
        else:
            cursor = coll.find(query, {"_id": 0}).skip(offset).limit(limit)
        
        docs = list(cursor)
        
        # Remove empty fields from each document
        cleaned_docs = [
            {k: v for k, v in doc.items() if v not in (None, "", [], {}, ())}
            for doc in docs
        ]

        message = f"{total_count} Approved CSI Records found. Showing page {page} with {len(cleaned_docs)} records."
        return {"status": "success", "message": message, "data": cleaned_docs}

    except PyMongoError as e:
        print(f"[APPROVED_CSI READ ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while fetching the Approved CSI Records.", "data": []}
    except Exception as e:
        print(f"[APPROVED_CSI READ ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}

def create_approved_csi(**kwargs) -> dict:
    """
    Create a new approved CSI record.
    This is typically only used internally by the system after a case is approved.
    
    Args:
        **kwargs: Fields for the approved CSI record
        
    Returns:
        dict: Contains status, message, and the created record data
    """
    print("[APPROVED_CSI CREATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[APPROVED_CSI CREATE] Got DB connection")
        coll = db[COLLECTION]

        # Add approval timestamp
        kwargs["approved_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        # Ensure csi_status is set to approved
        kwargs["csi_status"] = "approved"

        # Prepare document
        doc = dict(kwargs)
        print("[APPROVED_CSI CREATE] Document to insert:", doc)

        # Insert document
        result = coll.insert_one(doc)
        print(f"[APPROVED_CSI CREATE] Inserted with _id: {result.inserted_id}")

        # Retrieve the inserted document (excluding Mongo _id)
        inserted_doc = coll.find_one({"_id": result.inserted_id}, {"_id": 0})

        return {
            "status": "success",
            "message": "Approved CSI Record created successfully",
            "data": inserted_doc
        }

    except DuplicateKeyError:
        print("[APPROVED_CSI CREATE] DuplicateKeyError: Record with this ID already exists.")
        traceback.print_exc()
        return {
            "status": "error",
            "message": "Approved CSI Record with this ID already exists."
        }
    except PyMongoError as e:
        print("[APPROVED_CSI CREATE ERROR] PyMongoError occurred:", e)
        traceback.print_exc()
        return {
            "status": "error",
            "message": "An unexpected error occurred while creating the Approved CSI Record."
        }
    except Exception as e:
        print("[APPROVED_CSI CREATE ERROR] Generic error:", e)
        traceback.print_exc()
        return {
            "status": "error",
            "message": "An unexpected error occurred during the operation."
        }

def update_approved_csi(query_fields: dict, update_fields: dict) -> dict:
    """
    Update an approved CSI record based on query and update fields.
    
    Args:
        query_fields: Dictionary of fields to identify the record
        update_fields: Dictionary of fields to update
        
    Returns:
        dict: Contains status, message, and updated data if successful
    """
    print(f"[APPROVED_CSI UPDATE] Query fields: {query_fields}")
    print(f"[APPROVED_CSI UPDATE] Update fields: {update_fields}")
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[APPROVED_CSI UPDATE] Got DB connection")

        # Build query
        parsed_query = {}
        for k, v in query_fields.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        parsed_query["_id"] = ObjectId(v)
                    except Exception:
                        parsed_query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    parsed_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    parsed_query[k] = v

        print("[APPROVED_CSI UPDATE] Parsed query fields:", parsed_query)
        
        if not parsed_query:
            return {"status": "error", "message": "No query fields provided for update.", "data": []}
            
        if not update_fields:
            return {"status": "error", "message": "No update fields provided.", "data": []}

        # Check if record exists
        existing_doc = coll.find_one(parsed_query)
        if not existing_doc:
            return {"status": "error", "message": "No matching Approved CSI Record found. Update not performed.", "data": []}

        # Update modification timestamp
        update_fields["modified_at"] = datetime.datetime.now(datetime.timezone.utc)

        # Perform update
        result = coll.update_one({"_id": existing_doc["_id"]}, {"$set": update_fields})
        if result.modified_count > 0:
            updated_doc = coll.find_one({"_id": existing_doc["_id"]}, {"_id": 0})
            return {"status": "success", "message": "Approved CSI Record updated successfully.", "data": updated_doc}
        else:
            return {"status": "warning", "message": "No changes made to the Approved CSI Record.", "data": {}}

    except PyMongoError as e:
        print(f"[APPROVED_CSI UPDATE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while updating the Approved CSI Record.", "data": []}
    except Exception as e:
        print(f"[APPROVED_CSI UPDATE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}

def delete_approved_csi(query_fields: dict) -> dict:
    """
    Delete an approved CSI record based on query fields.
    
    Args:
        query_fields: Dictionary of fields to identify the record to delete
        
    Returns:
        dict: Contains status and message
    """
    print("[APPROVED_CSI DELETE] Called with query_fields:", query_fields)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[APPROVED_CSI DELETE] Got DB connection")
        
        # Build query
        parsed_query = {}
        for k, v in query_fields.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        parsed_query["_id"] = ObjectId(v)
                    except Exception:
                        parsed_query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    parsed_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    parsed_query[k] = v
                    
        if not parsed_query:
            return {"status": "error", "message": "No query fields provided for deletion.", "data": []}
            
        # Pre-check
        found = coll.find_one(parsed_query)
        if not found:
            return {"status": "error", "message": "No matching Approved CSI Record found. Deletion not performed.", "data": []}
        
        # Delete
        result = coll.delete_one(parsed_query)
        if result.deleted_count > 0:
            return {"status": "success", "message": "Approved CSI Record deleted successfully.", "data": []}
        else:
            return {"status": "error", "message": "Deletion failed.", "data": []}
    
    except PyMongoError as e:
        print(f"[APPROVED_CSI DELETE ERROR] PyMongoError: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred while deleting the Approved CSI Record.", "data": []}
    except Exception as e:
        print(f"[APPROVED_CSI DELETE ERROR] Exception: {e}")
        traceback.print_exc()
        return {"status": "error", "message": "An unexpected error occurred during the operation.", "data": []}