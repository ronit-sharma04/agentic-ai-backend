# tools/user_tools.py
from langchain_core.tools import tool
from crud.user_curd import create_user, read_user, update_user, delete_user

@tool
def create_user_tool(name: str, email: str) -> str:
    """Create a new user with a name and email."""
    return create_user(name, email)

@tool
def read_user_tool(user_id: int = None, name: str = None) -> str:
    """Read users by ID or partial name."""
    return read_user(user_id=user_id, name=name)

@tool
def update_user_tool(user_id: int, name: str = None, email: str = None) -> str:
    """Update a user's name and/or email by ID."""
    return update_user(user_id=user_id, name=name, email=email)

@tool
def delete_user_tool(user_id: int) -> str:
    """Delete a user by ID."""
    return delete_user(user_id=user_id)
