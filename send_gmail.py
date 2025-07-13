import requests

WEBHOOK_URL = "https://n8n.delivery-pre-uat.gocomet.com/webhook/send-mail"  # Replace this with your actual webhook

def send_to_webhook(data: str) -> dict:
    payload = {"data": data}
    response = requests.post(WEBHOOK_URL, json=payload)
    
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return {"status": "error", "message": "Invalid JSON response"}
    else:
        return {"status": "error", "message": f"HTTP {response.status_code}"}
