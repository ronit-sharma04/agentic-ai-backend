from pprint import pprint
from crud.cases_crud import read_cases,create_cases  # Replace with the correct path or module name

# Example 1: Basic read with no filters
from crud.cases_crud import read_cases  # Update path if needed
from pprint import pprint

print("=== Test 1: Basic call with multiple filters ===")

response = create_cases(
    page=1,
    sold_to_code="99000123",
    sold_to_comp_name="EXAMPLE TRADING CO. LTD.",
    sold_to_comp_add1="123 EXAMPLE STREET, BLOCK A, INDUSTRIAL ZONE",
    sold_to_comp_add2="EXAMPLIA CITY",
    sold_to_comp_add3="",  # This will be ignored by your read_cases logic
    sold_to_comp_add4="FANTASYLAND"
)

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
