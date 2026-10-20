"""
Problem: 175 - Combine Two Tables
Difficulty: Easy

Link:
https://leetcode.com/problems/combine-two-tables/

Time Complexity:
O(n*m)

Space Complexity:
O(n+m)

Notes:
n : # persons
m : # addresses
"""

import pandas as pd

def combine_two_tables(person: pd.DataFrame, address: pd.DataFrame) -> pd.DataFrame:
    newTable = []
    for _, p in person.iterrows():
        firstName = p["firstName"]
        lastName = p["lastName"]
        personId = p["personId"]

        addressRow = address[address["personId"] == personId]
        if addressRow.empty:
            city = state = None
        else:
            city = addressRow.iloc[0]["city"]
            state = addressRow.iloc[0]["state"]

        newTable.append({
            "firstName": firstName, 
            "lastName": lastName, 
            "city": city,
            "state": state
        })
    return pd.DataFrame(newTable, columns=['firstName', 'lastName', 'city', 'state'])           


def to_records(df):
    """Order-insensitive, NaN-insensitive view of a DataFrame."""
    records = [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.to_dict("records")
    ]
    return sorted(records, key=repr)


def run_tests():
    # Test 1
    person = pd.DataFrame([[1, 'Wang', 'Allen'], [2, 'Alice', 'Bob']], columns=['personId', 'lastName', 'firstName'])
    address = pd.DataFrame([[1, 2, 'New York City', 'New York'], [2, 3, 'Leetcode', 'California']], columns=['addressId', 'personId', 'city', 'state'])
    result = combine_two_tables(person, address)
    expected = pd.DataFrame([['Allen', 'Wang', None, None], ['Bob', 'Alice', 'New York City', 'New York']], columns=['firstName', 'lastName', 'city', 'state'])
    assert to_records(result) == to_records(expected)

    print("All tests passed.")


if __name__ == "__main__":
    run_tests()
