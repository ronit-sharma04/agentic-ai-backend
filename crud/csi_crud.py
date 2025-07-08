from db.connection import get_db_connection
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import re

COLLECTION = "cases"
from bson import ObjectId

def create_csi(**kwargs) -> str:
    print("[CREATE] Called with kwargs:", kwargs)
    try:
        db = get_db_connection(COLLECTION)
        print("[CREATE] Got DB connection")
        coll = db[COLLECTION]

        # Generate a new ObjectId
        _id = ObjectId()
        kwargs["_id"] = _id

        # Prepare document
        doc = dict(kwargs)
        print("[CREATE] Document to insert:", doc)

        # Insert document
        result = coll.insert_one(doc)
        print(f"[CREATE] Inserted with _id: {result.inserted_id}")
        return f"CSI row created with _id: {_id}"
    except DuplicateKeyError:
        print("[CREATE] DuplicateKeyError: Record with this _id already exists.")
        return '[CREATE ERROR] Record with this _id already exists.'
    except PyMongoError as e:
        print("[CREATE ERROR] PyMongoError occurred:", e)
        return "[CREATE ERROR] An unexpected error occurred while creating the record."
    except Exception as e:
        print("[CREATE ERROR] Generic error:", e)
        return "[CREATE ERROR] An unexpected error occurred during the operation."

def read_csi(**kwargs) -> str:
    print(f"[READ] Called with kwargs={kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        print("[READ] Got DB connection")
        coll = db[COLLECTION]
        query = {}
        for k, v in kwargs.items():
            if v is not None:
                if k == "id" or k == "_id":
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
        docs = list(coll.find(query))
        print(f"[READ] Found {len(docs)} docs")
        if not docs:
            print("[READ] No CSI records found.")
            return "No CSI records found."
        for d in docs:
            d.pop("_id", None)
        print("[READ] Returning docs:", docs)
        return "\n---\n".join([str(row) for row in docs])
    except PyMongoError as e:
        print("[READ ERROR] PyMongoError occurred:", e)
        return "[READ ERROR] An unexpected error occurred while fetching the records."
    except Exception as e:
        print("[READ ERROR] Generic error:", e)
        return "[READ ERROR] An unexpected error occurred during the operation."

def update_csi(filter_kwargs: dict, update_kwargs: dict) -> str:
    print(f"[UPDATE] Called with filter_kwargs={filter_kwargs}, update_kwargs={update_kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        print("[UPDATE] Got DB connection")
        coll = db[COLLECTION]
        filter_query = {}
        for k, v in filter_kwargs.items():
            if v is not None:
                if k == "id" or k == "_id":
                    try:
                        filter_query["_id"] = ObjectId(v)
                    except Exception:
                        filter_query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    filter_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    filter_query[k] = v
        update_fields = {k: v for k, v in update_kwargs.items() if v is not None and k not in ["id", "_id"]}
        print("[UPDATE] Filter query:", filter_query)
        print("[UPDATE] Update fields:", update_fields)
        if not update_fields:
            print("[UPDATE] No valid fields to update.")
            return "[UPDATE ERROR] No valid fields to update."
        result = coll.update_many(filter_query, {"$set": update_fields})
        print(f"[UPDATE] Matched: {result.matched_count}, Modified: {result.modified_count}")
        if result.matched_count:
            return f"Updated {result.modified_count} record(s) successfully."
        else:
            print("[UPDATE] No CSI record found matching filter.")
            return "No CSI record found matching filter."
    except PyMongoError as e:
        print("[UPDATE ERROR] PyMongoError occurred:", e)
        return "[UPDATE ERROR] An unexpected error occurred while updating the record."
    except Exception as e:
        print("[UPDATE ERROR] Generic error:", e)
        return "[UPDATE ERROR] An unexpected error occurred during the operation."

def delete_csi(**kwargs) -> str:
    print(f"[DELETE] Called with kwargs={kwargs}")
    try:
        db = get_db_connection(COLLECTION)
        print("[DELETE] Got DB connection")
        coll = db[COLLECTION]
        filter_query = {}
        for k, v in kwargs.items():
            if v is not None:
                if k == "id" or k == "_id":
                    try:
                        filter_query["_id"] = ObjectId(v)
                    except Exception:
                        filter_query["_id"] = v
                elif isinstance(v, str):
                    pattern = re.escape(v)
                    filter_query[k] = {"$regex": pattern, "$options": "i"}
                else:
                    filter_query[k] = v
        print("[DELETE] Filter query:", filter_query)
        result = coll.delete_many(filter_query)
        print(f"[DELETE] Deleted count: {result.deleted_count}")
        if result.deleted_count:
            return f"Deleted {result.deleted_count} record(s) successfully."
        else:
            print("[DELETE] No CSI record found matching filter.")
            return "No CSI record found matching filter."
    except PyMongoError as e:
        print("[DELETE ERROR] PyMongoError occurred:", e)
        return "[DELETE ERROR] An unexpected error occurred while deleting the record."
    except Exception as e:
        print("[DELETE ERROR] Generic error:", e)
        return "[DELETE ERROR] An unexpected error occurred during the operation."