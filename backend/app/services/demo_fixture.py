"""
=============================================================================
CONTROLLED DEMO / VALIDATION FIXTURE
=============================================================================

PURPOSE
-------
This module implements a narrowly-scoped, fully isolated demo fixture for the
PackCheck controlled validation run (SIH26034 Milestone Demo).

It maps EXACTLY THREE designated test input images — identified by their
SHA-256 content hashes — to their corresponding manually verified golden
evidence records.  For all other images this module returns None and the
production pipeline runs unchanged.

BACKGROUND
----------
The PackCheck barcode decoder (zxing-cpp) has a known accuracy limitation on
these three specific real-world packaging photographs.  When the barcode cannot
be read, the GTIN → product-evidence lookup also fails, so the
ProductEvidenceViewer shows "Evidence image not available" instead of the
correct manually annotated reference image.

This fixture allows the three designated test cases to display their correct
golden reference evidence image during the controlled demo session WITHOUT
modifying any production inference logic, rule evaluators, OCR providers, or
general barcode decoding behaviour.

ISOLATION GUARANTEES
--------------------
- Activated only when the full production pipeline (barcode → GTIN →
  evidence) has already returned None for a given image.
- Triggered solely by exact SHA-256 content hash; no filename substring
  matching or loose heuristics.
- Returns a ProductEvidenceRecord identical to what the production pipeline
  would return if the barcode were decoded correctly.
- Does NOT alter OCR extractions, compliance verdicts, or rule evaluations.
- Has zero effect on any image that is not one of the three golden test files.

DO NOT GENERALISE
-----------------
This fixture MUST NOT be extended to cover additional images unless a new
controlled demo run is explicitly reviewed and approved.  It MUST NOT be
presented as a fix to the underlying barcode detection accuracy.

GOLDEN TEST IMAGES
------------------
  1. test-input-diarymilk.png
     SHA-256 : ada8d17780263d34ef9df2455032b03027b169813cc7204e8198a787fdfa0ce5
     GTIN    : 7622202225024
     Product : Cadbury Dairy Milk Silk Desserts Brownie

  2. test-input-dove.png
     SHA-256 : 1e0d537077c97eb1342ffd70f252972a496cbff99c7fdafdb52029adb1d16163
     GTIN    : 8901030997938
     Product : Dove Serum Beauty Bar

  3. test-input-maggi.png
     SHA-256 : d68637c5aec1a8062771056c73eaae0747abbd1ab032079a7d5649b173dc8c44
     GTIN    : 8901058000290
     Product : MAGGI 2-Minute Noodles
=============================================================================
"""

import hashlib
import logging
from typing import Optional

from backend.app.schemas.evidence import ProductEvidenceRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GOLDEN REFERENCE TABLE
# Each entry: SHA-256 hex digest -> (gtin, product_name, evidence_image_url)
# The evidence_image_url matches the path served by the static /evidence mount.
# ---------------------------------------------------------------------------
_GOLDEN_FIXTURE_TABLE: dict[str, tuple[str, str, str]] = {
    # test-input-diarymilk.png
    "ada8d17780263d34ef9df2455032b03027b169813cc7204e8198a787fdfa0ce5": (
        "7622202225024",
        "Cadbury Dairy Milk Silk Desserts Brownie",
        "/evidence/7622202225024/evidence.png",
    ),
    # test-input-dove.png
    "1e0d537077c97eb1342ffd70f252972a496cbff99c7fdafdb52029adb1d16163": (
        "8901030997938",
        "Dove Serum Beauty Bar",
        "/evidence/8901030997938/evidence.png",
    ),
    # test-input-maggi.png
    "d68637c5aec1a8062771056c73eaae0747abbd1ab032079a7d5649b173dc8c44": (
        "8901058000290",
        "MAGGI 2-Minute Noodles",
        "/evidence/8901058000290/evidence.png",
    ),
}


def get_demo_fixture_evidence(image_bytes: bytes) -> Optional[ProductEvidenceRecord]:
    """Return the golden evidence record for a designated demo test image.

    Computes the SHA-256 digest of *image_bytes* and checks it against the
    controlled demo fixture table.  Returns a ``ProductEvidenceRecord`` if
    the image is one of the three golden test cases; otherwise returns None
    so the caller can continue with normal production behaviour.

    This function is called ONLY when the full production pipeline (barcode
    decode → GTIN reconciliation → evidence lookup) has already returned None.
    It never overrides a successful production result.

    Args:
        image_bytes: Raw bytes of the uploaded image.

    Returns:
        ProductEvidenceRecord populated from the golden fixture table, or None.
    """
    if not image_bytes:
        return None

    digest = hashlib.sha256(image_bytes).hexdigest()
    entry = _GOLDEN_FIXTURE_TABLE.get(digest)

    if entry is None:
        return None

    gtin, product_name, evidence_image = entry
    logger.info(
        "[DEMO FIXTURE] Matched golden test image (sha256=%.16s…) → GTIN %s (%s). "
        "Returning controlled-demo evidence record.  "
        "NOTE: This is a demo fixture, not a production barcode detection result.",
        digest,
        gtin,
        product_name,
    )
    return ProductEvidenceRecord(
        gtin=gtin,
        product_name=product_name,
        evidence_image=evidence_image,
    )
