"""Deterministic local GTIN validation module.

Implements standard GS1 Modulo-10 check-digit validation across:
- GTIN-8 (EAN-8)
- GTIN-12 (UPC-A)
- GTIN-13 (EAN-13)
- GTIN-14 (ITF-14 / GS1-128)

Pure algorithm: NO network calls, NO external APIs, completely offline.
"""

from typing import NamedTuple, Optional

from backend.app.schemas.barcode import BarcodeFormat, GTINValidationStatus

# Standard GTIN lengths recognized by GS1
SUPPORTED_GTIN_LENGTHS = {8, 12, 13, 14}


class GTINValidationResult(NamedTuple):
    """Result of validating a candidate GTIN string."""

    is_valid: bool
    status: GTINValidationStatus
    message: str
    normalized_gtin: Optional[str]


def calculate_gtin_check_digit(payload_digits: str) -> int:
    """Calculate the GS1 Modulo-10 check digit from payload digits.

    According to the GS1 General Specifications:
    Numbering positions from right to left (excluding the check digit):
    - Position 1 (immediately adjacent to the check digit) has weight 3
    - Position 2 has weight 1
    - Position 3 has weight 3
    - Alternating weights 3, 1, 3, 1 ...

    Formula:
        sum = sum(d_i * (3 if i is even else 1)) for i in 0..N-1 (reversed)
        check_digit = (10 - (sum % 10)) % 10

    Args:
        payload_digits: Numeric string of digits preceding the check digit
            (e.g., 7 digits for GTIN-8, 11 for GTIN-12, 12 for GTIN-13, 13 for GTIN-14).

    Returns:
        Integer check digit in the range [0, 9].

    Raises:
        ValueError: If payload_digits is empty or contains non-digit characters.
    """
    if not payload_digits:
        raise ValueError("Cannot calculate check digit for empty payload.")

    if not payload_digits.isdigit():
        raise ValueError(
            f"Payload contains non-digit characters: '{payload_digits}'"
        )

    # Reverse payload so position 1 (rightmost payload digit) gets weight 3
    weighted_sum = sum(
        int(digit) * (3 if idx % 2 == 0 else 1)
        for idx, digit in enumerate(reversed(payload_digits))
    )

    remainder = weighted_sum % 10
    return 0 if remainder == 0 else (10 - remainder)


def validate_gtin(
    raw_value: Optional[str],
    barcode_format: Optional[BarcodeFormat] = None,
) -> GTINValidationResult:
    """Validate a candidate GTIN string deterministically.

    Performs structural and check-digit validation:
    1. Null / empty check
    2. Format compatibility check
    3. Numeric check
    4. Length check (8, 12, 13, 14)
    5. Modulo-10 check-digit verification

    Args:
        raw_value: Decoded barcode text or candidate GTIN string.
        barcode_format: Optional detected barcode format.

    Returns:
        GTINValidationResult with is_valid, status, message, and normalized_gtin.
    """
    if raw_value is None:
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.EMPTY,
            message="No barcode value provided (None).",
            normalized_gtin=None,
        )

    cleaned = raw_value.strip()
    if not cleaned:
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.EMPTY,
            message="Barcode value is empty or contains only whitespace.",
            normalized_gtin=None,
        )

    # Check for formats known to not be standard retail GTINs
    non_gtin_formats = {BarcodeFormat.QR_CODE, BarcodeFormat.DATA_MATRIX}
    if barcode_format in non_gtin_formats:
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.NOT_A_GTIN_FORMAT,
            message=f"Barcode format '{barcode_format.value}' is not a standard GTIN retail carrier.",
            normalized_gtin=None,
        )

    # Check if value contains non-numeric characters
    if not cleaned.isdigit():
        if barcode_format == BarcodeFormat.CODE_128:
            return GTINValidationResult(
                is_valid=False,
                status=GTINValidationStatus.NOT_A_GTIN_FORMAT,
                message=f"Code 128 barcode value '{cleaned}' is alphanumeric and does not represent a GTIN.",
                normalized_gtin=None,
            )
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.NON_NUMERIC,
            message=f"GTIN candidate contains non-numeric characters: '{cleaned}'.",
            normalized_gtin=None,
        )

    # Check length
    val_len = len(cleaned)
    if val_len not in SUPPORTED_GTIN_LENGTHS:
        if barcode_format == BarcodeFormat.CODE_128:
            return GTINValidationResult(
                is_valid=False,
                status=GTINValidationStatus.NOT_A_GTIN_FORMAT,
                message=f"Code 128 barcode length ({val_len}) does not match GTIN standards (8, 12, 13, 14).",
                normalized_gtin=None,
            )
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.INVALID_LENGTH,
            message=f"Invalid GTIN length: {val_len} digits. Expected 8, 12, 13, or 14 digits.",
            normalized_gtin=None,
        )

    # Check digit calculation
    payload = cleaned[:-1]
    expected_check_digit = calculate_gtin_check_digit(payload)
    actual_check_digit = int(cleaned[-1])

    if actual_check_digit != expected_check_digit:
        return GTINValidationResult(
            is_valid=False,
            status=GTINValidationStatus.INVALID_CHECK_DIGIT,
            message=(
                f"Invalid check digit for GTIN-{val_len}: expected {expected_check_digit}, "
                f"got {actual_check_digit}."
            ),
            normalized_gtin=cleaned,
        )

    return GTINValidationResult(
        is_valid=True,
        status=GTINValidationStatus.VALID,
        message=f"Valid GTIN-{val_len} check digit ({actual_check_digit}).",
        normalized_gtin=cleaned,
    )
