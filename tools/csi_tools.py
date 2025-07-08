from langchain_core.tools import tool
from typing import Optional
from crud.csi_crud import create_csi, read_csi, update_csi, delete_csi
from pydantic import ValidationError,BaseModel
import logging

@tool
def read_csi_tool(id: Optional[str] = None, sold_to_comp_name: Optional[str] = None) -> str:
    """
    Read CSI records by id (string, unique record id) or by partial sold_to_comp_name.
    """
    print(f"[READ TOOL] Called with id={id}, sold_to_comp_name={sold_to_comp_name}")
    return read_csi(id=id, sold_to_comp_name=sold_to_comp_name)

@tool
def delete_csi_tool(id: str) -> str:
    """Delete a CSI record by id."""
    print(f"[DELETE TOOL] Called with id={id}")
    return delete_csi(id=id)

class CSIToolArgs(BaseModel):
    sold_to_code: Optional[str] = ""
    sold_to_comp_name: Optional[str] = ""
    # Add other fields as needed

@tool
def create_csi_tool(inputs: CSIToolArgs) -> str:
    """
    Create a CSI record. Accepts any fields from the schema except '_id'.
    """
    logging.debug("create_csi_tool called with inputs: %s", inputs)
    try:
        # Convert inputs to a dictionary
        data = inputs.model_dump()

        # Call the create function
        result = create_csi(**data)
        logging.debug("create_csi result: %s", result)
        return result
    except ValidationError as e:
        logging.error("Validation error in create_csi_tool: %s", e)
        return "[CREATE ERROR] Validation error occurred."
    except Exception as e:
        logging.error("Error in create_csi_tool: %s", e)
        return "[CREATE ERROR] An unexpected error occurred."