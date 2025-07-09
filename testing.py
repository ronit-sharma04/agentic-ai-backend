from pprint import pprint
from crud.cases_crud import read_csi  # Replace with the correct path or module name

# Example 1: Basic read with no filters
print("=== Test 1: Basic call ===")
response = read_csi(page=5, sold_to_comp_name="AL GURG UNILEVER (LLC)")  # No filters, just pagination
pprint(response)

# Example 2: Pagination - page 2
# print("\n=== Test 2: Pagination (page 2) ===")
# response = read_csi(offset=5, page=2)
# pprint(response)

# # Example 3: Filter by string field
# print("\n=== Test 3: Filter by string field ===")
# response = read_csi(name="Alice")  # Replace 'name' with an actual field in your collection
# pprint(response)

# # Example 4: Filter by ObjectId
# print("\n=== Test 4: Filter by ObjectId ===")
# response = read_csi(_id="64a7db9ee1c2a0e0d4a01234")  # Use a real ObjectId from your DB
# pprint(response)

# Example 5: Invalid ObjectId
# print("\n=== Test 5: Invalid ObjectId ===")
# response = read_csi(_id="not-a-valid-id")
# pprint(response)
