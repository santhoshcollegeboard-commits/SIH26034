"""Unit tests for deterministic local GTIN validation.

Tests standard GS1 Modulo-10 check-digit validation across:
- GTIN-8 (EAN-8)
- GTIN-12 (UPC-A)
- GTIN-13 (EAN-13)
- GTIN-14 (ITF-14)
Along with structural checks, edge cases, and failure modes.
"""

import pytest

from backend.app.schemas.barcode import BarcodeFormat, GTINValidationStatus
from backend.app.services.barcode.validator import (
    calculate_gtin_check_digit,
    validate_gtin,
)


# =============================================================================
# 1. GS1 Modulo-10 Check Digit Calculation Unit Tests
# =============================================================================

def test_calculate_check_digit_gtin8():
    """Verify check digit calculation for 7-digit payload (GTIN-8)."""
    # 9638507 -> check digit 4 (full GTIN-8: 96385074)
    assert calculate_gtin_check_digit("9638507") == 4


def test_calculate_check_digit_gtin12():
    """Verify check digit calculation for 11-digit payload (GTIN-12 / UPC-A)."""
    # 01234567890 -> check digit 5 (full GTIN-12: 012345678905)
    assert calculate_gtin_check_digit("01234567890") == 5


def test_calculate_check_digit_gtin13():
    """Verify check digit calculation for 12-digit payload (GTIN-13 / EAN-13)."""
    # 890103089201 -> check digit 1 (full GTIN-13: 8901030892011)
    assert calculate_gtin_check_digit("890103089201") == 1
    # Parle-G 800g: 890171910103 -> check digit 8 (full GTIN-13: 8901719101038)
    assert calculate_gtin_check_digit("890171910103") == 8


def test_calculate_check_digit_gtin14():
    """Verify check digit calculation for 13-digit payload (GTIN-14 / ITF-14)."""
    # 1001234567890 -> check digit 2 (full GTIN-14: 10012345678902)
    assert calculate_gtin_check_digit("1001234567890") == 2


def test_calculate_check_digit_zero_check_digit():
    """Verify check digit when weighted sum is an exact multiple of 10."""
    # 0000000 -> weighted sum 0 -> check digit 0
    assert calculate_gtin_check_digit("0000000") == 0


def test_calculate_check_digit_invalid_inputs():
    """Verify ValueError is raised on non-numeric or empty payload."""
    with pytest.raises(ValueError, match="empty payload"):
        calculate_gtin_check_digit("")

    with pytest.raises(ValueError, match="non-digit"):
        calculate_gtin_check_digit("89010308920A")


# =============================================================================
# 2. GTIN-8 Validation Tests
# =============================================================================

def test_gtin8_valid():
    """Valid GTIN-8 passes validation."""
    res = validate_gtin("96385074", BarcodeFormat.EAN_8)
    assert res.is_valid is True
    assert res.status == GTINValidationStatus.VALID
    assert res.normalized_gtin == "96385074"
    assert "Valid GTIN-8" in res.message


def test_gtin8_invalid_check_digit():
    """GTIN-8 with wrong check digit fails with INVALID_CHECK_DIGIT."""
    # Correct is 4, provide 5
    res = validate_gtin("96385075", BarcodeFormat.EAN_8)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.INVALID_CHECK_DIGIT
    assert res.normalized_gtin == "96385075"
    assert "expected 4, got 5" in res.message


# =============================================================================
# 3. GTIN-12 (UPC-A) Validation Tests
# =============================================================================

def test_gtin12_valid():
    """Valid GTIN-12 passes validation."""
    res = validate_gtin("012345678905", BarcodeFormat.UPC_A)
    assert res.is_valid is True
    assert res.status == GTINValidationStatus.VALID
    assert res.normalized_gtin == "012345678905"
    assert "Valid GTIN-12" in res.message


def test_gtin12_invalid_check_digit():
    """GTIN-12 with wrong check digit fails with INVALID_CHECK_DIGIT."""
    # Correct is 5, provide 4
    res = validate_gtin("012345678904", BarcodeFormat.UPC_A)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.INVALID_CHECK_DIGIT
    assert "expected 5, got 4" in res.message


# =============================================================================
# 4. GTIN-13 (EAN-13) Validation Tests
# =============================================================================

def test_gtin13_valid():
    """Valid GTIN-13 passes validation."""
    res = validate_gtin("8901030892011", BarcodeFormat.EAN_13)
    assert res.is_valid is True
    assert res.status == GTINValidationStatus.VALID
    assert res.normalized_gtin == "8901030892011"
    assert "Valid GTIN-13" in res.message

    # Real FMCG barcode
    res2 = validate_gtin("8901719101038", BarcodeFormat.EAN_13)
    assert res2.is_valid is True
    assert res2.status == GTINValidationStatus.VALID


def test_gtin13_invalid_check_digit():
    """GTIN-13 with wrong check digit fails with INVALID_CHECK_DIGIT."""
    # 8901030892014 was the made-up number in create_samples.py (expected 1)
    res = validate_gtin("8901030892014", BarcodeFormat.EAN_13)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.INVALID_CHECK_DIGIT
    assert "expected 1, got 4" in res.message


# =============================================================================
# 5. GTIN-14 Validation Tests
# =============================================================================

def test_gtin14_valid():
    """Valid GTIN-14 passes validation."""
    res = validate_gtin("10012345678902", BarcodeFormat.ITF_14)
    assert res.is_valid is True
    assert res.status == GTINValidationStatus.VALID
    assert res.normalized_gtin == "10012345678902"
    assert "Valid GTIN-14" in res.message


def test_gtin14_invalid_check_digit():
    """GTIN-14 with wrong check digit fails with INVALID_CHECK_DIGIT."""
    # Correct is 2, provide 1
    res = validate_gtin("10012345678901", BarcodeFormat.ITF_14)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.INVALID_CHECK_DIGIT
    assert "expected 2, got 1" in res.message


# =============================================================================
# 6. Edge Cases & Safe Failure Handling
# =============================================================================

@pytest.mark.parametrize("invalid_len_code", [
    "1234567",         # 7 digits
    "123456789",       # 9 digits
    "1234567890",      # 10 digits
    "12345678901",     # 11 digits
    "123456789012345", # 15 digits
])
def test_gtin_invalid_length(invalid_len_code: str):
    """Numbers that do not match 8, 12, 13, or 14 digits return INVALID_LENGTH."""
    res = validate_gtin(invalid_len_code)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.INVALID_LENGTH
    assert "Invalid GTIN length" in res.message


def test_gtin_non_numeric():
    """Alphanumeric input fails with NON_NUMERIC."""
    res = validate_gtin("890103089201A")
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.NON_NUMERIC
    assert "non-numeric" in res.message


def test_gtin_empty_string():
    """Empty string or whitespace returns EMPTY."""
    res = validate_gtin("")
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.EMPTY

    res_ws = validate_gtin("   \t  ")
    assert res_ws.is_valid is False
    assert res_ws.status == GTINValidationStatus.EMPTY


def test_gtin_none():
    """None value returns EMPTY safely."""
    res = validate_gtin(None)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.EMPTY
    assert "None" in res.message


def test_gtin_whitespace_stripping():
    """Leading and trailing whitespace should be stripped cleanly."""
    res = validate_gtin("  8901030892011 \n")
    assert res.is_valid is True
    assert res.status == GTINValidationStatus.VALID
    assert res.normalized_gtin == "8901030892011"


def test_code128_alphanumeric_not_gtin():
    """Code 128 containing alphanumeric SKU is NOT_A_GTIN_FORMAT, not a crash."""
    res = validate_gtin("SKU-BOX-9988", BarcodeFormat.CODE_128)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.NOT_A_GTIN_FORMAT
    assert "alphanumeric" in res.message


def test_qrcode_not_gtin():
    """2D QR Code is flagged as NOT_A_GTIN_FORMAT."""
    res = validate_gtin("https://example.com/product", BarcodeFormat.QR_CODE)
    assert res.is_valid is False
    assert res.status == GTINValidationStatus.NOT_A_GTIN_FORMAT
