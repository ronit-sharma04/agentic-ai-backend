import requests
import logging

def fetch_analysis_logic_from_n8n():
    """Fetch analysis logic from n8n endpoint"""
    # Replace this URL with your actual n8n endpoint
    N8N_URL = "https://n8n.delivery-pre-uat.gocomet.com/webhook/fetch-updated-logic"
    
    try:
        response = requests.get(N8N_URL, timeout=10)
        if response.status_code == 200:
            # Try to get content from response - adjust based on your n8n response format
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                # Adjust these field names based on your n8n response structure
                content = data.get('content') or data.get('text') or data.get('analysis_logic') or str(data)
            else:
                content = response.text
            
            if content and len(content.strip()) > 50:
                logging.info(f"[ANALYSIS] Fetched {len(content)} characters from n8n")
                return content.strip()
        
        logging.warning(f"[ANALYSIS] Failed to fetch from n8n: {response.status_code}")
        return None
        
    except Exception as e:
        logging.error(f"[ANALYSIS] Error fetching from n8n: {e}")
        return None
