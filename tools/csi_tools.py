from langchain_core.tools import tool
from crud.csi_crud import create_csi, read_csi, update_csi, delete_csi, bulk_delete_csi

@tool
def create_csi_tool(row: dict) -> str:
    """Create a CSI record. Provide a dict with all available fields. 'csi_id' is required."""
    return create_csi(row)

@tool
def read_csi_tool(csi_id: str = None, sold_to_name: str = None) -> str:
    """Read CSI records by csi_id or partial sold_to_name."""
    return read_csi(csi_id=csi_id, sold_to_name=sold_to_name)

@tool
def update_csi_tool(csi_id: str, updates: dict) -> str:
    """Update a CSI record. Provide csi_id and a dict of updates."""
    return update_csi(csi_id=csi_id, updates=updates)

@tool
def delete_csi_tool(csi_id: str) -> str:
    """Delete a CSI record by csi_id."""
    return delete_csi(csi_id=csi_id)

@tool
def bulk_delete_csi_tool(criteria: dict) -> str:
    """Bulk delete CSI records by criteria dict. All keys must match columns."""
    return bulk_delete_csi(**criteria)