"""Tests for Step 8 — Backend foundation for the REVIEW stage.

Covers:
A. REVIEW_REQUIRED evaluation is correctly identified.
B. Review response exposes rule ID, reason, field/value, confidence, source_region, what_to_verify.
C. Reviewer confirms an extracted value.
D. Reviewer corrects an extracted value.
E. Corrected value is passed back through the deterministic rule engine.
F. Reviewer cannot directly force PASS/FAIL by submitting a status.
G. Original AI value and confidence remain available after reviewer correction (provenance).
H. Invalid reviewer input is rejected.
I. Missing/unassessable evidence is handled safely.
J. Full regression and API contracts.
"""

from copy import deepcopy
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.schemas.review import (
    FieldCorrection,
    ReviewAction,
    ReviewItemsRequest,
    ReviewSubmissionRequest,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_extraction_baseline():
    """Baseline extraction where all Rule 6 declarations pass."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Basmati Rice",
            confidence=0.95,
            status="extracted",
            source_region=SourceRegion(x=50, y=50, width=200, height=40),
        ),
        manufacturer_name=ExtractedField(
            value="Himalayan Foods Ltd",
            confidence=0.92,
            status="extracted",
            source_region=SourceRegion(x=50, y=100, width=300, height=35),
        ),
        manufacturer_address=ExtractedField(
            value="123 Industrial Area, Sector 5, Haridwar, Uttarakhand - 249401",
            confidence=0.91,
            status="extracted",
            source_region=SourceRegion(x=50, y=140, width=400, height=50),
        ),
        packer_name=ExtractedField(status="not_found"),
        importer_name=ExtractedField(status="not_found"),
        net_quantity=ExtractedField(
            value="5 kg",
            confidence=0.98,
            status="extracted",
            source_region=SourceRegion(x=100, y=250, width=120, height=40),
        ),
        mrp=ExtractedField(
            value="MRP Rs. 450.00 (incl. of all taxes)",
            confidence=0.94,
            status="extracted",
            source_region=SourceRegion(x=150, y=300, width=250, height=40),
        ),
        month_year_of_manufacture=ExtractedField(
            value="08/2024",
            confidence=0.90,
            status="extracted",
            source_region=SourceRegion(x=80, y=360, width=140, height=30),
        ),
        consumer_care_details=ExtractedField(
            value="Manager, Consumer Care, care@himalayanfoods.com, 1800-111-2222, 123 Industrial Area, Haridwar",
            confidence=0.93,
            status="extracted",
            source_region=SourceRegion(x=50, y=410, width=380, height=45),
        ),
    )


# --- TEST A & B: Identify review-required evaluations and expose fields ---


def test_identify_review_required_items(client, valid_extraction_baseline):
    """Test A: REVIEW_REQUIRED evaluations are correctly identified.
    Test B: Response exposes rule ID, reason, field, value, confidence, source region, what_to_verify.
    """
    # Create extraction with low confidence on net_quantity to trigger REVIEW_REQUIRED
    extraction = deepcopy(valid_extraction_baseline)
    extraction.net_quantity = ExtractedField(
        value="5 kg",
        confidence=0.55,  # Below 0.70 threshold -> REVIEW_REQUIRED
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=120, height=40),
    )

    response = client.post(
        "/api/review/items",
        json={"extraction": extraction.model_dump(), "rules": [6]},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["requires_human_review"] is True
    assert data["review_required_count"] >= 1
    assert data["initial_disposition"] == ComplianceVerdict.REVIEW_REQUIRED.value

    # Find the net_quantity review item
    net_q_item = next(
        (item for item in data["review_items"] if item["rule_id"] == "LMR-2011-R06-01C-NET-QTY"),
        None,
    )
    assert net_q_item is not None

    # Test B: Verify all required fields are exposed
    assert net_q_item["rule_id"] == "LMR-2011-R06-01C-NET-QTY"
    assert "Rule 6(1)(c)" in net_q_item["statutory_reference"]
    assert net_q_item["rule_status"] == ComplianceVerdict.REVIEW_REQUIRED.value
    assert "confidence" in net_q_item["reason_for_review"].lower()
    assert net_q_item["field_name"] == "net_quantity"
    assert net_q_item["observed_value"] == "5 kg"
    assert net_q_item["confidence"] == 0.55
    assert net_q_item["source_region"] == {"x": 100, "y": 250, "width": 120, "height": 40}
    assert "metric units" in net_q_item["what_to_verify"].lower()


# --- TEST C: Reviewer confirms an extracted value ---


def test_reviewer_confirms_extracted_value(client, valid_extraction_baseline):
    """Test C: Reviewer confirms an extracted value with low confidence.

    Low confidence caused REVIEW_REQUIRED. Inspector confirmation establishes certainty (1.0)
    and deterministic re-evaluation transitions disposition to PASS.
    """
    extraction = deepcopy(valid_extraction_baseline)
    extraction.net_quantity = ExtractedField(
        value="5 kg",
        confidence=0.52,
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=120, height=40),
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "confirm",
                "reviewer_notes": "Confirmed 5 kg is distinctly printed on front label.",
            }
        ],
        "rules": [6],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["initial_disposition"] == ComplianceVerdict.REVIEW_REQUIRED.value
    assert data["final_disposition"] == ComplianceVerdict.PASS.value
    assert data["requires_further_review"] is False

    # Updated extraction has confidence upgraded to 1.0
    assert data["updated_extraction"]["net_quantity"]["confidence"] == 1.0
    assert data["updated_extraction"]["net_quantity"]["value"] == "5 kg"

    # Provenance correctly reflects action
    prov = data["provenance"]["net_quantity"]
    assert prov["action_taken"] == "confirmed"
    assert prov["original_confidence"] == 0.52
    assert prov["reviewer_notes"] == "Confirmed 5 kg is distinctly printed on front label."


# --- TEST D & E: Reviewer corrects extracted value & deterministic re-evaluation ---


def test_reviewer_corrects_extracted_value(client, valid_extraction_baseline):
    """Test D: Reviewer corrects an extracted value.
    Test E: Corrected value is passed back through the deterministic rule engine.

    AI extracted '500' without metric unit (non-compliant -> FAIL).
    Reviewer corrects to '500 g'. Rule engine re-evaluates '500 g' and returns PASS.
    """
    extraction = deepcopy(valid_extraction_baseline)
    extraction.net_quantity = ExtractedField(
        value="500",  # Missing metric unit -> statutory violation
        confidence=0.85,
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=120, height=40),
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "correct",
                "corrected_value": "500 g",
                "source_region": {"x": 100, "y": 250, "width": 140, "height": 40},
                "reviewer_notes": "Added missing 'g' unit clearly visible adjacent to 500.",
            }
        ],
        "rules": [6],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["initial_disposition"] == ComplianceVerdict.FAIL.value
    assert data["final_disposition"] == ComplianceVerdict.PASS.value

    # Rule evaluation for Rule 6(1)(c) is PASS after re-evaluation
    rule_6_1_c = next(
        e for e in data["compliance"]["rule_evaluations"] if e["rule_id"] == "LMR-2011-R06-01C-NET-QTY"
    )
    assert rule_6_1_c["status"] == ComplianceVerdict.PASS.value
    assert "500 g" in str(rule_6_1_c["observed_value"])


# --- TEST F: Reviewer cannot directly force PASS/FAIL by submitting status ---


def test_reviewer_cannot_force_status_bypass(client, valid_extraction_baseline):
    """Test F: Reviewer cannot directly force PASS/FAIL by submitting a status.

    Attempts to pass a compliance status in the submission payload or field correction
    are strictly rejected with HTTP 422 Unprocessable Entity due to extra='forbid'.
    """
    extraction = deepcopy(valid_extraction_baseline)
    # Missing MRP entirely -> statutory violation (FAIL)
    extraction.mrp = ExtractedField(status="not_found")

    # Attempt 1: Inject top-level 'status'
    payload_top_level_status = {
        "original_extraction": extraction.model_dump(),
        "corrections": [],
        "status": "PASS",  # ILLEGAL BYPASS ATTEMPT
    }
    res1 = client.post("/api/review/submit", json=payload_top_level_status)
    assert res1.status_code == 422

    # Attempt 2: Inject top-level 'verdict'
    payload_top_level_verdict = {
        "original_extraction": extraction.model_dump(),
        "corrections": [],
        "verdict": "PASS",  # ILLEGAL BYPASS ATTEMPT
    }
    res2 = client.post("/api/review/submit", json=payload_top_level_verdict)
    assert res2.status_code == 422

    # Attempt 3: Inject 'status' inside a FieldCorrection
    payload_nested_status = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "mrp",
                "action": "confirm",
                "status": "PASS",  # ILLEGAL BYPASS ATTEMPT
            }
        ],
    }
    res3 = client.post("/api/review/submit", json=payload_nested_status)
    assert res3.status_code == 422


# --- TEST G: Original AI value and confidence remain available (provenance) ---


def test_provenance_preservation(client, valid_extraction_baseline):
    """Test G: Original AI value and confidence remain available after reviewer correction."""
    extraction = deepcopy(valid_extraction_baseline)
    extraction.mrp = ExtractedField(
        value="Rs. 40",
        confidence=0.45,
        status="extracted",
        source_region=SourceRegion(x=150, y=300, width=100, height=30),
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "mrp",
                "action": "correct",
                "corrected_value": "MRP Rs. 40.00 (incl. of all taxes)",
                "reviewer_notes": "Corrected full statutory phrase from label.",
            }
        ],
        "rules": [6],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    mrp_prov = data["provenance"]["mrp"]
    # Original AI extraction preserved intact
    assert mrp_prov["original_value"] == "Rs. 40"
    assert mrp_prov["original_confidence"] == 0.45
    assert mrp_prov["original_status"] == "extracted"
    assert mrp_prov["original_source_region"] == {"x": 150, "y": 300, "width": 100, "height": 30}

    # Review resolution recorded distinctly
    assert mrp_prov["reviewed_value"] == "MRP Rs. 40.00 (incl. of all taxes)"
    assert mrp_prov["action_taken"] == "corrected"
    assert mrp_prov["reviewed_at"] is not None


# --- TEST H: Invalid reviewer input is rejected ---


def test_invalid_reviewer_input_rejected(client, valid_extraction_baseline):
    """Test H: Invalid reviewer input is rejected safely."""
    extraction = deepcopy(valid_extraction_baseline)

    # Case 1: Unknown field name
    bad_field_payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "non_existent_field",
                "action": "confirm",
            }
        ],
    }
    r1 = client.post("/api/review/submit", json=bad_field_payload)
    assert r1.status_code == 422

    # Case 2: Action 'correct' with missing or empty corrected_value
    missing_value_payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "correct",
                "corrected_value": "",  # Empty
            }
        ],
    }
    r2 = client.post("/api/review/submit", json=missing_value_payload)
    assert r2.status_code == 422

    # Case 3: Invalid action string
    invalid_action_payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "bypass_rules",  # Invalid action
            }
        ],
    }
    r3 = client.post("/api/review/submit", json=invalid_action_payload)
    assert r3.status_code == 422


# --- TEST I: Marking evidence as unassessable is handled safely ---


def test_reviewer_marks_unassessable(client, valid_extraction_baseline):
    """Test I: Reviewer marks evidence as unassessable.

    Deterministic rule engine evaluates unreadable field and reflects statutory outcome.
    """
    extraction = deepcopy(valid_extraction_baseline)
    # AI extracted blurry MRP text
    extraction.mrp = ExtractedField(
        value="???",
        confidence=0.30,
        status="extracted",
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "mrp",
                "action": "mark_unassessable",
                "reviewer_notes": "Price declaration is torn and completely obscured.",
            }
        ],
        "rules": [6],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Provenance shows marked_unassessable
    assert data["provenance"]["mrp"]["action_taken"] == "marked_unassessable"
    assert data["updated_extraction"]["mrp"]["value"] is None
    assert data["updated_extraction"]["mrp"]["status"] == "unreadable"

    # Deterministic rule engine produces REVIEW_REQUIRED because unreadable mandatory MRP requires recapture/review
    assert data["final_disposition"] == ComplianceVerdict.REVIEW_REQUIRED.value


# --- TEST: Physical calibration metadata provided during review ---


def test_physical_metadata_update_during_review(client, valid_extraction_baseline):
    """Test reviewer providing physical calibration metadata to resolve Rule 7.

    Rule 7 requires physical scale (mm_per_pixel) to calculate numeral height.
    Providing mm_per_pixel in package_metadata resolves Rule 7 from REVIEW_REQUIRED to PASS.
    """
    extraction = deepcopy(valid_extraction_baseline)
    extraction.net_quantity = ExtractedField(
        value="500 g",
        confidence=0.95,
        status="extracted",
        # Height 40 px at 0.08 mm/px = 3.2 mm (statutory requirement for 500g is >= 2mm)
        source_region=SourceRegion(x=100, y=250, width=120, height=40),
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "confirm",
                "reviewer_notes": "Physical measurement calibrated with ruler.",
            }
        ],
        "package_metadata": {
            "physical_mm_per_pixel": 0.08,
        },
        "rules": [7],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Rule 7 numeral height evaluation is PASS
    rule_7_eval = next(
        e for e in data["compliance"]["rule_evaluations"] if e["rule_id"] == "LMR-2011-R07-02-NUMERAL-HEIGHT"
    )
    assert rule_7_eval["status"] == ComplianceVerdict.PASS.value


def test_multiple_field_corrections_in_single_batch(client, valid_extraction_baseline):
    """Test submitting multiple field resolutions simultaneously in a single review request."""
    extraction = deepcopy(valid_extraction_baseline)
    extraction.net_quantity = ExtractedField(
        value="1000",
        confidence=0.60,
        status="extracted",
    )
    extraction.mrp = ExtractedField(
        value="Rs. 99",
        confidence=0.50,
        status="extracted",
    )

    payload = {
        "original_extraction": extraction.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "correct",
                "corrected_value": "1 kg",
                "reviewer_notes": "Added standard metric kg.",
            },
            {
                "field_name": "mrp",
                "action": "correct",
                "corrected_value": "MRP Rs. 99.00 (incl. of all taxes)",
                "reviewer_notes": "Added mandatory tax inclusion statement.",
            },
            {
                "field_name": "product_name",
                "action": "confirm",
                "reviewer_notes": "Confirmed product name is visible.",
            },
        ],
        "rules": [6],
    }

    response = client.post("/api/review/submit", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["final_disposition"] == ComplianceVerdict.PASS.value
    assert data["provenance"]["net_quantity"]["action_taken"] == "corrected"
    assert data["provenance"]["net_quantity"]["reviewed_value"] == "1 kg"
    assert data["provenance"]["mrp"]["action_taken"] == "corrected"
    assert data["provenance"]["product_name"]["action_taken"] == "confirmed"


def test_get_review_items_with_pre_existing_inspection(client, valid_extraction_baseline):
    """Test that /api/review/items can consume an already-evaluated InspectionResult."""
    extraction = deepcopy(valid_extraction_baseline)
    pre_inspection = {
        "overall_disposition": "REVIEW_REQUIRED",
        "rule_evaluations": [
            {
                "rule_id": "LMR-2011-R06-01C-NET-QTY",
                "rule_version": "LMR-2011-BASE-R06",
                "rule_name": "Net Quantity Declaration",
                "status": "REVIEW_REQUIRED",
                "explanation": "Ambiguous unit; review needed.",
                "observed_value": "500",
                "expected_requirement": "Metric unit",
            }
        ],
    }

    response = client.post(
        "/api/review/items",
        json={
            "extraction": extraction.model_dump(),
            "inspection": pre_inspection,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["requires_human_review"] is True
    assert len(data["review_items"]) == 1
    assert data["review_items"][0]["rule_id"] == "LMR-2011-R06-01C-NET-QTY"
    assert data["review_items"][0]["reason_for_review"] == "Ambiguous unit; review needed."

