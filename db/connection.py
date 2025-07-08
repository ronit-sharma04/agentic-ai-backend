from pymongo import MongoClient
import os

_connection_logged = False
_collection_checked = {}

def get_db_connection(collection_name=None):
    global _connection_logged, _collection_checked
    uri = os.getenv("MONGODB_URI", "mongodb://gocomet1:gocomet123@35.207.230.78:47017/")
    db_name = os.getenv("MONGODB_DB", "agentic_ai_delivery_pre_uat")
    client = MongoClient(uri)
    db = client[db_name]
    if not _connection_logged:
        print(f"[DB] Successfully connected to MongoDB at {uri}, database: {db_name}")
        _connection_logged = True
    if collection_name and collection_name not in _collection_checked:
        if collection_name in db.list_collection_names():
            print(f"[DB] Collection '{collection_name}' exists in database '{db_name}'.")
        else:
            # Create collection by inserting a dummy doc and deleting it
            db.create_collection(collection_name)
            print(f"[DB] Collection '{collection_name}' did not exist and was created in database '{db_name}'.")
        _collection_checked[collection_name] = True
    return db