from pymongo import MongoClient
import os
import atexit
import logging

class DatabaseManager:
    """
    Singleton database manager that maintains a persistent MongoDB connection
    with connection pooling for improved performance.
    """
    _instance = None
    _client = None
    _db = None
    _connection_logged = False
    _collection_checked = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """
        Initialize MongoDB connection with connection pooling settings.
        """
        try:
            uri = os.getenv("MONGODB_URI", "mongodb://gocomet1:gocomet123@35.207.230.78:47017/")
            db_name = os.getenv("MONGODB_DB", "agentic_ai_delivery_pre_uat")
            
            # Connection pooling configuration
            self._client = MongoClient(
                uri,
                maxPoolSize=50,  # Maximum number of connections in the pool
                minPoolSize=5,   # Minimum number of connections in the pool
                maxIdleTimeMS=30000,  # Close connections after 30 seconds of inactivity
                waitQueueTimeoutMS=5000,  # Wait up to 5 seconds for a connection from the pool
                serverSelectionTimeoutMS=5000,  # Wait up to 5 seconds for server selection
                connectTimeoutMS=10000,  # 10 second connection timeout
                socketTimeoutMS=20000,   # 20 second socket timeout
            )
            
            self._db = self._client[db_name]
            
            # Test the connection
            self._client.admin.command('ping')
            
            if not self._connection_logged:
                print(f"[DB] Successfully connected to MongoDB at {uri}, database: {db_name}")
                print(f"[DB] Connection pool configured: maxPoolSize=50, minPoolSize=5")
                self._connection_logged = True
            
            # Register cleanup function
            atexit.register(self.close_connection)
            
        except Exception as e:
            logging.error(f"[DB] Failed to initialize MongoDB connection: {e}")
            raise
    
    def get_database(self, collection_name=None):
        """
        Get the database instance, ensuring collection exists if specified.
        
        Args:
            collection_name: Optional collection name to check/create
            
        Returns:
            Database instance
        """
        if self._db is None:
            self._initialize_connection()
        
        # Handle collection creation/verification
        if collection_name and collection_name not in self._collection_checked:
            try:
                if collection_name in self._db.list_collection_names():
                    print(f"[DB] Collection '{collection_name}' exists in database.")
                else:
                    # Create collection
                    self._db.create_collection(collection_name)
                    print(f"[DB] Collection '{collection_name}' created in database.")
                self._collection_checked[collection_name] = True
            except Exception as e:
                logging.warning(f"[DB] Error handling collection '{collection_name}': {e}")
        
        return self._db
    
    def get_collection(self, collection_name):
        """
        Get a specific collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection instance
        """
        db = self.get_database(collection_name)
        return db[collection_name]
    
    def close_connection(self):
        """
        Close the MongoDB connection and cleanup resources.
        """
        if self._client:
            print("[DB] Closing MongoDB connection...")
            self._client.close()
            self._client = None
            self._db = None
    
    def get_connection_info(self):
        """
        Get information about the current connection pool.
        
        Returns:
            dict: Connection pool statistics
        """
        if self._client:
            try:
                # Get server info
                server_info = self._client.server_info()
                return {
                    "connected": True,
                    "server_version": server_info.get("version", "unknown"),
                    "database_name": self._db.name if self._db else "unknown"
                }
            except Exception as e:
                return {"connected": False, "error": str(e)}
        return {"connected": False}

# Global database manager instance
_db_manager = DatabaseManager()

def get_db_connection(collection_name=None):
    """
    Get database connection using the singleton database manager.
    This function maintains backward compatibility while using connection pooling.
    
    Args:
        collection_name: Optional collection name to check/create
        
    Returns:
        Database instance
    """
    return _db_manager.get_database(collection_name)

def get_db_collection(collection_name):
    """
    Get a specific collection using the connection pool.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection instance
    """
    return _db_manager.get_collection(collection_name)

def initialize_db_connection():
    """
    Initialize the database connection at server startup.
    This should be called when the server starts.
    """
    global _db_manager
    _db_manager._initialize_connection()
    print("[DB] Database connection pool initialized successfully")

def close_db_connection():
    """
    Close the database connection.
    This should be called when the server shuts down.
    """
    global _db_manager
    _db_manager.close_connection()

def get_db_connection_info():
    """
    Get information about the current database connection.
    
    Returns:
        dict: Connection information
    """
    global _db_manager
    return _db_manager.get_connection_info()