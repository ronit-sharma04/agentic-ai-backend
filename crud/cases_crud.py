from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random
COLLECTION = "cases"
from bson import ObjectId
from fetch_process_activity_status import fetch_process_activity_status
def read_cases(page: int = 1, **kwargs) -> dict:
    print(f"[READ] Called with kwargs={kwargs}, page={page}")
    try:
        db = get_db_connection(COLLECTION)
        print("[READ] Got DB connection")
        coll = db[COLLECTION]

        # Build query
        query = {}
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

        print("[READ] Query:", query)

        total_count = coll.count_documents(query)
        print(f"[READ] Total matching docs: {total_count}")
        if total_count==0 & page>=1:
            return {"message": "CSI cases for this page number finished.", "data": []}
        elif total_count == 0:
            return {"message": "No CSI Cases found.", "data": []}

        limit = 5
        offset = (page - 1) * limit

        docs = list(coll.find(query, {"_id": 0}).skip(offset).limit(limit))

        message = f"{total_count} Cases found. Showing page {page} with {len(docs)} Cases."
        return {"message": message, "data": docs}

    except PyMongoError:
        return {"message": "An unexpected error occurred while fetching the Cases.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}
    

import random
from pymongo.errors import DuplicateKeyError, PyMongoError

def create_cases(**kwargs) -> dict:
    print("[CREATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[CREATE] Got DB connection")
        coll = db[COLLECTION]

        # Add default fields
        case_id = f"csi-case-{random.randint(100000, 999999)}"
        kwargs["case_id"] = case_id
        kwargs["csi_status"] = "pending"

        # Add process_activity from n8n
        process_activity = fetch_process_activity_status()
        kwargs["process_activity"] = process_activity

        # Prepare document
        doc = dict(kwargs)
        print("[CREATE] Document to insert:", doc)

        # Insert document
        result = coll.insert_one(doc)
        print(f"[CREATE] Inserted with _id: {result.inserted_id}")

        # Retrieve the inserted document (excluding Mongo _id)
        inserted_doc = coll.find_one({"_id": result.inserted_id}, {"_id": 0})

        return {
            "message": f"Case opened successfully with ID: {case_id}",
            "case_id": case_id,
            "data": inserted_doc
        }

    except DuplicateKeyError:
        print("[CREATE] DuplicateKeyError: Case with this case_id already exists.")
        return {
            "error": True,
            "message": "Case with this case_id already exists."
        }
    except PyMongoError as e:
        print("[CREATE ERROR] PyMongoError occurred:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred while creating the Case."
        }
    except Exception as e:
        print("[CREATE ERROR] Generic error:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred during the operation."
        }


def approve_cases(**kwargs) -> dict:
    print("[APPROVE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[APPROVE] Got DB connection")
        cases_coll = db[COLLECTION]
        approved_coll = db["approved_csi"]

        # Build query similar to read_cases
        query = {}
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

        print("[APPROVE] Query:", query)

        # Find matching cases
        matching_cases = list(cases_coll.find(query))
        print(f"[APPROVE] Found {len(matching_cases)} matching cases.")

        if not matching_cases:
            return {"message": "No matching CSI Cases found to approve.", "data": []}

        approved_cases = []

        for case in matching_cases:
            # Update status
            case["csi_status"] = "approved"

            # Remove _id to prevent duplication errors in new collection
            if "_id" in case:
                case.pop("_id")

            approved_cases.append(case)

        # Insert into approved_csi collection
        if approved_cases:
            approved_coll.insert_many(approved_cases)
            print(f"[APPROVE] Inserted {len(approved_cases)} approved cases into 'approved_csi'.")

        # Update original documents in `cases` collection
        update_result = cases_coll.update_many(query, {"$set": {"csi_status": "approved"}})
        print(f"[APPROVE] Updated {update_result.modified_count} documents in 'cases'.")

        return {
            "message": f"Approved {len(approved_cases)} case(s).",
            "data": approved_cases
        }

    except PyMongoError as e:
        print("[APPROVE ERROR] PyMongoError occurred:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred while approving the Cases."
        }
    except Exception as e:
        print("[APPROVE ERROR] Generic error:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred during the operation."
        }


def update_case(**kwargs) -> dict:
    print("[UPDATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[UPDATE] Got DB connection")
        coll = db[COLLECTION]

        # Separate query fields and update fields
        query_fields = {}
        update_fields = kwargs.copy()

        for k, v in kwargs.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        query_fields["_id"] = ObjectId(v)
                    except Exception:
                        query_fields["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    query_fields[k] = {"$regex": pattern, "$options": "i"}
                else:
                    query_fields[k] = v

        print("[UPDATE] Query fields:", query_fields)

        # Find the first matching document
        existing_doc = coll.find_one(query_fields)
        if not existing_doc:
            print("[UPDATE] No matching case found.")
            return {
                "message": "No matching Case found. Update not performed.",
                "data": []
            }

        print("[UPDATE] Found existing case:", existing_doc)

        # Prevent updating by identifier fields
        for key in query_fields:
            update_fields.pop(key, None)

        if not update_fields:
            return {
                "message": "No update fields provided after filtering query keys.",
                "data": []
            }

        # Perform update
        result = coll.update_one({"_id": existing_doc["_id"]}, {"$set": update_fields})
        if result.modified_count > 0:
            updated_doc = coll.find_one({"_id": existing_doc["_id"]}, {"_id": 0})
            print("[UPDATE] Updated case:", updated_doc)
            return {
                "message": "Case updated successfully.",
                "data": updated_doc
            }
        else:
            print("[UPDATE] No changes made.")
            return {
                "message": "No changes made to the Case.",
                "data": existing_doc
            }

    except PyMongoError as e:
        print("[UPDATE ERROR] PyMongoError:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred while updating the Case."
        }
    except Exception as e:
        print("[UPDATE ERROR] Exception:", e)
        return {
            "error": True,
            "message": "An unexpected error occurred during the operation."
        }

def delete_csi(**kwargs) -> dict:
    print("[DELETE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        # Build query
        query = {}
        for k, v in kwargs.items():
            if v is not None:
                if k in ("id", "_id"):
                    try:
                        query["_id"] = ObjectId(v)
                    except Exception:
                        query["_id"] = v
                else:
                    query[k] = v
        # Pre-check
        found = coll.find_one(query)
        if not found:
            return {"message": "No matching Case found. Deletion not performed.", "data": []}
        # Delete
        result = coll.delete_one(query)
        if result.deleted_count > 0:
            return {"message": "Case deleted successfully.", "data": []}
        else:
            return {"message": "Deletion failed.", "data": []}
    except PyMongoError:
        return {"message": "An unexpected error occurred while deleting the Case.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}


def get_case_object_id_by_query(query: dict) -> str:
    """
    Returns the ObjectId (as string) of the first matching case, or None.
    """
    print("[GET CASE OBJECT ID] Called with query:", query)
    db = get_db_connection(COLLECTION)
    coll = db[COLLECTION]
    doc = coll.find_one(query)
    print("[GET CASE OBJECT ID] Found document:", doc)
    if doc and "_id" in doc:
        return str(doc["_id"])
    return None