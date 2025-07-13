from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re
import random

COLLECTION = "approved_csi"

def find_in_approved_csi_collection(page: int = 1, **kwargs) -> dict:
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
        print(f"[READ] Total matching records: {total_count}")
        if total_count == 0:
            return {"message": "No Approved CSI Records found.", "data": []}

        limit = 2
        offset = (page - 1) * limit

        docs = list(coll.find(query, {"_id": 0}).skip(offset).limit(limit))

        message = f"{total_count} Approved CSI Records found. Showing page {page} with {len(docs)} records."
        return {"message": message, "data": docs}

    except PyMongoError:
        return {"message": "An unexpected error occurred while fetching the Approved CSI Records.", "data": []}
    except Exception:
        return {"message": "An unexpected error occurred during the operation.", "data": []}


from db.connection import get_db_connection
from pymongo.errors import PyMongoError
from bson import ObjectId
import re

COLLECTION = "approved_csi"

def update_approved_csi_record(**kwargs) -> dict:
    print(f"[UPDATE] Called with kwargs={kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        coll = db[COLLECTION]
        print("[UPDATE] Got DB connection")

        # Separate filters and update fields
        filter_query = {}
        update_fields = {}
        for k, v in kwargs.items():
            if v is None or v == "":
                continue
            if k in ("id", "_id"):
                try:
                    filter_query["_id"] = ObjectId(v)
                except Exception:
                    filter_query["_id"] = v
            elif k.startswith("update__"):
                # update__fieldname=value → {"fieldname": value}
                update_key = k.replace("update__", "")
                update_fields[update_key] = v
            else:
                if isinstance(v, str):
                    pattern = re.escape(v)
                    filter_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    filter_query[k] = v

        print("[UPDATE] Filter query:", filter_query)
        print("[UPDATE] Update fields:", update_fields)

        if not filter_query:
            return {"message": "No filters provided for update.", "updated": False}
        if not update_fields:
            return {"message": "No update fields provided.", "updated": False}

        result = coll.update_one(filter_query, {"$set": update_fields})

        if result.matched_count == 0:
            return {"message": "No matching Approved CSI records found to update.", "updated": False}
        if result.modified_count == 0:
            return {"message": "Record matched but no changes were made (fields may already have the same values).", "updated": False}

        return {
            "message": f"Successfully updated {result.modified_count} Approved CSI record(s).",
            "updated": True
        }

    except PyMongoError as e:
        print(f"[UPDATE ERROR] PyMongoError: {e}")
        return {"message": "An unexpected error occurred while updating Approved CSI record.", "updated": False}
    except Exception as e:
        print(f"[UPDATE ERROR] Exception: {e}")
        return {"message": "An unexpected error occurred during update operation.", "updated": False}