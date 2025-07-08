import logging
from crud.csi_crud import create_csi

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_create_csi():
    # Example data
    csi_data = {
        "id": "ronit",  # Ensure this is unique or adjust as needed
        "sold_to_code": "example_code"
    }

    # Call the create_csi function
    logging.info("Attempting to create CSI record with data: %s", csi_data)
    result = create_csi(**csi_data)
    logging.info("Result: %s", result)

if __name__ == "__main__":
    test_create_csi()