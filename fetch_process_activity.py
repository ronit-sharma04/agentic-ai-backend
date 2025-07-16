import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_process_activity():
    url = "https://n8n.delivery-pre-uat.gocomet.com/webhook/extract-process-activty"
    try:
        response = requests.get(url, verify=False)  # Skip SSL check
        response.raise_for_status()
        data = response.json()
        return data.get("content", "")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return ""

if __name__ == "__main__":
    print(fetch_process_activity())
