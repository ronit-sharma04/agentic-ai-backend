from langchain_core.tools import tool
from bson import ObjectId
from crud.cases_crud import get_case_object_id_by_query
from tools.cases_args import CSIToolArgs


@tool
def render_create_form_tool() -> dict:
    """
    Renders a form for creating a CSI record. Generates and returns a new ObjectId as a placeholder.
    """
    print("[FORM RENDER CREATE TOOL] Called")
    return {
        "message": "render-create-form",
        "data": [{"_id": str(ObjectId())}]
    }
render_create_form_tool.name = "form_render_create_tool"


@tool
def render_update_form_tool(inputs: CSIToolArgs) -> dict:
    """
    Renders a form for updating a CSI record by fetching the ObjectId based on user-provided query parameters.
    Returns message and _id if found, otherwise a message with empty data.
    """
    print("[FORM RENDER UPDATE TOOL] Called with inputs:", inputs)
    data = {k: v for k, v in inputs.model_dump().items() if v not in ("", None)}

    object_id = get_case_object_id_by_query(data)
    if object_id:
        return {
            "message": "render-update-form",
            "data": [{"_id": str(object_id)}]
        }
    else:
        return {
            "message": "No data found for the given query to update.",
            "data": []
        }
render_update_form_tool.name = "form_render_update_tool"


@tool
def render_delete_confirmation_tool(inputs: dict) -> dict:
    """
    Renders a delete confirmation for a CSI record based on query parameters.
    Returns the ObjectId if found, else a message with empty data.
    """
    print("[FORM RENDER DELETE TOOL] Called with inputs:", inputs)
    object_id = get_case_object_id_by_query(inputs)
    if object_id:
        return {
            "message": "render-delete-confirmation",
            "data": [{"_id": str(object_id)}]
        }
    else:
        return {
            "message": "No data found for the given query to delete.",
            "data": []
        }
render_delete_confirmation_tool.name = "form_render_delete_tool"
