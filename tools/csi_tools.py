from langchain_core.tools import tool
from crud.cases_crud import create_csi, read_cases, update_csi, delete_csi
from pydantic import ValidationError
from tools.cases_args import CSIToolArgs
import logging


@tool
def read_cases_tool(inputs: CSIToolArgs) -> str:
    """
    Reads CSI records based on filter parameters such as id, csi_id, sold_to_comp_name, etc.
    Supports pagination using `offset` and `page`.
    Returns a summary message and up to 5 matching records.
    """
    data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}
    print(f"[CSI READ TOOL] Called with inputs={data}")
    result = read_cases(**data)
    print(f"[CSI READ TOOL] Result: {result}")
    return result
read_cases_tool.name = "csi_read_tool"


@tool
def create_csi_tool(inputs: CSIToolArgs) -> str:
    """
    Creates a new CSI record using the provided data (excluding '_id').
    """
    try:
        data = inputs.model_dump()
        result = create_csi(**data)
        return result
    except ValidationError as e:
        logging.error("Validation error in create_csi_tool: %s", e)
        return "[CREATE ERROR] Validation error occurred."
    except Exception as e:
        logging.error("Error in create_csi_tool: %s", e)
        return "[CREATE ERROR] An unexpected error occurred."
create_csi_tool.name = "csi_create_tool"


@tool
def update_csi_tool(inputs: CSIToolArgs) -> str:
    """
    Updates a CSI record. Requires `csi_id` along with the fields to update.
    """
    data = inputs.model_dump()
    csi_id = data.get("csi_id")
    if not csi_id:
        return {"message": "csi_id is required for update.", "data": []}
    result = update_csi(csi_id, **data)
    return result
update_csi_tool.name = "csi_update_tool"


@tool
def delete_csi_tool(inputs: CSIToolArgs) -> str:
    """
    Deletes a CSI record using the provided filter criteria.
    """
    data = inputs.model_dump()
    result = delete_csi(**data)
    return result
delete_csi_tool.name = "csi_delete_tool"
