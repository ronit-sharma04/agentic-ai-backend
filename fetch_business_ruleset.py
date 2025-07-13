import requests

def fetch_business_ruleset():
    url = "https://n8n.delivery-pre-uat.gocomet.com/webhook/extract-business-ruleset"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("content", "")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return ""

# Only run this when script is executed directly
if __name__ == "__main__":
    print(fetch_business_ruleset())
