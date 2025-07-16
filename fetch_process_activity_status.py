import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_process_activity_status():
    url = "https://n8n.delivery-pre-uat.gocomet.com/webhook/process-activity-status"
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        data = response.json()
        result = data.get("result", [])
        if isinstance(result, list):
            return result
        elif isinstance(result, str):
            return [result]
        else:
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching process activity: {e}")
        return []

if __name__ == "__main__":
    print(fetch_process_activity_status())
