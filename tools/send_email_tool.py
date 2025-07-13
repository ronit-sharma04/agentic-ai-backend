# tools/email_tools.py
from langchain_core.tools import tool
import requests

WEBHOOK_URL = "https://n8n.delivery-pre-uat.gocomet.com/webhook/send-mail"

@tool
def send_email_tool(email_content: str) -> dict:
    """
    Sends an email to BDM for sign-off using the n8n webhook.

    INPUT:
    - email_content: A string containing the full CSI case details formatted for email (e.g., JSON or plain text)

    USAGE:
    - This tool should be triggered **only** when the user explicitly indicates that the form has been submitted
      after the render-create-csi-form step.
    - The string must include all required CSI case data clearly formatted for BDM review.
    - Use only when user prompt confirms readiness for BDM sign-off or mentions form submission.
    """
    print("[SEND EMAIL TOOL] Called with content:", email_content)

    try:
        response = requests.post(WEBHOOK_URL, json={"content": email_content})
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "message": f"Failed with HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

send_email_tool.name = "send_email_tool"
