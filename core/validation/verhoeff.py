"""
Verhoeff Checksum Algorithm Implementation.
Used for validating the checksum digit of Indian 12-digit Aadhaar numbers.
Reference: UIDAI Aadhaar Validation Standards.
"""

# The multiplication table (d)
_D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# The permutation table (p)
_P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# The inverse table (inv)
_INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(number: str) -> bool:
    """
    Validate a numeric string using the Verhoeff algorithm.
    Returns True if valid, False otherwise.
    """
    if not isinstance(number, str) or not number.isdigit() or len(number) == 0:
        return False

    c = 0
    # Reverse string to process digits from right to left
    reversed_digits = list(map(int, reversed(number)))

    for i, digit in enumerate(reversed_digits):
        c = _D_TABLE[c][_P_TABLE[i % 8][digit]]

    return c == 0


def calculate_verhoeff_checksum(number: str) -> int:
    """
    Calculate the Verhoeff checksum digit for an 11-digit string.
    Returns the 12th checksum digit.
    """
    if not isinstance(number, str) or not number.isdigit():
        raise ValueError("Input must be a numeric string")

    c = 0
    reversed_digits = list(map(int, reversed(number)))

    for i, digit in enumerate(reversed_digits):
        c = _D_TABLE[c][_P_TABLE[(i + 1) % 8][digit]]

    return _INV_TABLE[c]
