from langchain.tools import tool
from fetch_business_ruleset import fetch_business_ruleset
from fetch_process_activity import fetch_process_activity

@tool
def fetch_mandatory_fields_tool() -> str:
    """
    No input is required for this function 
    Fetches the current mandatory fields required for CSI record creation or update.
    This tool retrieves the latest ruleset for mandatory fields by calling the fetch_business_ruleset function from the business_ruleset module.
    Call this tool whenever the intent is to create a CSI record or when any other intent requires validation against mandatory fields.

    Returns:
        string: A string containing the list of mandatory fields.
    """
    print(fetch_business_ruleset())
    return fetch_business_ruleset()
fetch_mandatory_fields_tool.name = "fetch_mandatory_fields_tool"

@tool
def fetch_process_activity_tool() -> str:
    """
    No input is required for this function 
    Fetches the process activity steps for creating or updating CSI records.
    This tool retrieves the latest process activity steps by calling the fetch_process_activity function from the process_activity module.
    Call this tool whenever the intent is to create or update a CSI record to guide the form rendering process.
    
    Args:
        inputs (dict): Input parameters (not used in this case but included for compatibility).
    
    Returns:
        dict: A dictionary containing the process activity steps.
    """
    print("fetched process activity: ",fetch_process_activity())
    return fetch_process_activity()
fetch_process_activity_tool.name = "fetch_process_activity_tool"