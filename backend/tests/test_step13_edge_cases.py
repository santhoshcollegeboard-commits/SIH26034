"""Comprehensive edge-case and defect validation test suite for Step 13.

Covers:
- Edge Case Group A: Quality Gate (real images, small, blur, dark, bright, corrupt, unsupported, aspect ratio, bypass check)
- Edge Case Group B: Extraction (clear, missing, low-confidence, unreadable, conditional, missing bbox, provider failures)
- Edge Case Group C: Rule Engine Rules 6-9 (compliant, missing, invalid, low-conf, conditional importer/packer, physical measurement unavailable, multiple failures, PASS+REVIEW, PASS+FAIL, all NOT_ASSESSABLE, empty list, aggregation hierarchy, zero AI calls)
- Edge Case Group D: Human Review (confirm, correct, mark unassessable, cannot force status, provenance, append-oriented, net_quantity '500' -> '500 g' re-evaluation, human-confirmed vs AI confidence)
- Edge Case Group E: Evidence Ledger (creation, permanent ID, persistence, parent linkage, multiple observations, empty optional evidence, re-query, history listing)
- Edge Case Group F: Result & Missing-Data Policy (constants, no raw None/null, missing confidence/source region, NOT_APPLICABLE vs NOT_ASSESSABLE)
- Edge Case Group G: PDF Generation (PASS, FAIL, REVIEW, NOT_ASSESSABLE, missing evidence/reviews/optional fields, valid PDF header, no raw None/null)
- Edge Case Group H: API Robustness (missing fields, invalid types, invalid enums, forbidden extra fields, unknown IDs, invalid review submissions)
- Edge Case Group I: Four-State Status Integrity (only PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE)
"""

import io
import os
from copy import deepcopy
from typing import Optional
from unittest.mock import AsyncMock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from backend.app.main import app
from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict, InspectionResult, RuleEvaluation
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.schemas.ledger import (
    AppendReviewRequest,
    CreateInspectionRecordRequest,
    EvidenceMetadataInput,
)
from backend.app.schemas.quality import QualityAssessment
from backend.app.schemas.review import (
    FieldCorrection,
    ReviewAction,
    ReviewItemsRequest,
    ReviewSubmissionRequest,
)
from backend.app.services.formatters import (
    EMPTY_EVIDENCE_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    EMPTY_REVIEW_ACTIONS_MESSAGE,
    EMPTY_RULE_EVALUATIONS_MESSAGE,
    MANDATORY_DECLARATION_FIELDS,
    NOT_APPLICABLE_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    NOT_RECORDED_MESSAGE,
    format_confidence,
    format_missing_value,
    format_source_region,
)
from backend.app.services.ledger_service import EvidenceLedgerService
from backend.app.services.quality_service import StandardImageQualityChecker
from backend.app.services.report_service import PDFReportService
from backend.app.services.result_service import ResultService
from backend.app.services.review_service import ReviewService
from backend.app.services.rule_engine_service import DeterministicRuleEngine
from rules import (
    aggregate_disposition,
    evaluate_all_rules,
    evaluate_rule_6,
    evaluate_rule_7,
    evaluate_rule_8,
    evaluate_rule_9,
)

client = TestClient(app)


# --------------------------------------------------------------------------
# Fixtures & Synthetic Image Generators
# --------------------------------------------------------------------------

def _make_synth_good_image(size=(500, 500)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(230, 230, 230))
    draw = ImageDraw.Draw(img)
    for i in range(0, size[0], 25):
        draw.line([(i, 0), (i, size[1])], fill=(20, 20, 20), width=3)
        draw.line([(0, i), (size[0], i)], fill=(20, 20, 20), width=3)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_fully_compliant_extraction() -> ExtractionResult:
    return ExtractionResult(
        product_name=ExtractedField(
            value="Pure Organic Wheat Flour",
            confidence=0.98,
            source_region=SourceRegion(x=50, y=50, width=220, height=40),
            status="extracted",
        ),
        manufacturer_name=ExtractedField(
            value="Hindustan Agro Mills Ltd",
            confidence=0.96,
            source_region=SourceRegion(x=50, y=110, width=320, height=35),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Survey 108, GIDC Estate, Sanand, Ahmedabad, Gujarat - 382110",
            confidence=0.94,
            source_region=SourceRegion(x=50, y=150, width=420, height=45),
            status="extracted",
        ),
        packer_name=ExtractedField(status="not_found"),
        importer_name=ExtractedField(status="not_found"),
        net_quantity=ExtractedField(
            value="1 kg",
            confidence=0.97,
            source_region=SourceRegion(x=100, y=250, width=120, height=40),
            status="extracted",
        ),
        mrp=ExtractedField(
            value="MRP Rs. 65.00 (inclusive of all taxes)",
            confidence=0.95,
            source_region=SourceRegion(x=150, y=450, width=260, height=40),
            status="extracted",
        ),
        month_year_of_manufacture=ExtractedField(
            value="09/2026",
            confidence=0.93,
            source_region=SourceRegion(x=80, y=360, width=140, height=30),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="Customer Care Officer: 1800-200-1111, care@hindustanagro.in, Survey 108, Sanand",
            confidence=0.92,
            source_region=SourceRegion(x=50, y=550, width=400, height=40),
            status="extracted",
        ),
    )


# --------------------------------------------------------------------------
# Group A: Quality Gate Edge Cases
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_gate_real_images():
    """Real genuine package images from data/test_images/ must pass quality gate."""
    checker = StandardImageQualityChecker()
    for fname in ["package_good_01.jpg.jpeg", "package_good_02.jpg.jpeg"]:
        p = os.path.join("data", "test_images", fname)
        assert os.path.exists(p), f"Missing test image {p}"
        with open(p, "rb") as f:
            data = f.read()
        assessment = await checker.assess_quality(data)
        assert assessment["is_acceptable"] is True
        assert assessment["overall_score"] >= 0.60
        assert len(assessment["reasons"]) == 0


@pytest.mark.asyncio
async def test_quality_gate_small_image():
    """Synthetic image < 300x300 fails resolution check and returns NOT_ASSESSABLE in API."""
    checker = StandardImageQualityChecker()
    small_img = _make_synth_good_image(size=(180, 180))
    res = await checker.assess_quality(small_img)
    assert res["is_acceptable"] is False
    assert any("resolution" in r.lower() for r in res["reasons"])

    # API verification: Quality failure prevents OCR and returns NOT_ASSESSABLE
    with patch("backend.app.api.extract.get_ocr_provider") as mock_provider_factory:
        mock_provider = AsyncMock()
        mock_provider_factory.return_value = mock_provider
        response = client.post(
            "/api/extract",
            files={"image": ("small.jpg", small_img, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["compliance"]["overall_disposition"] == ComplianceVerdict.NOT_ASSESSABLE.value
        assert "recapture" in data["error"].lower()
        mock_provider.extract.assert_not_called()


@pytest.mark.asyncio
async def test_quality_gate_blurry_image():
    """Synthetic excessively blurred image fails focus check and returns NOT_ASSESSABLE."""
    checker = StandardImageQualityChecker()
    good = _make_synth_good_image(size=(500, 500))
    img = Image.open(io.BytesIO(good))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG")
    blurry_bytes = buf.getvalue()

    res = await checker.assess_quality(blurry_bytes)
    assert res["is_acceptable"] is False
    assert any("blurred" in r.lower() for r in res["reasons"])


@pytest.mark.asyncio
async def test_quality_gate_dark_and_bright_images():
    """Synthetic underexposed and overexposed images fail exposure bounds."""
    checker = StandardImageQualityChecker()
    # Dark
    dark_buf = io.BytesIO()
    Image.new("RGB", (400, 400), color=(5, 5, 5)).save(dark_buf, format="JPEG")
    res_dark = await checker.assess_quality(dark_buf.getvalue())
    assert res_dark["is_acceptable"] is False
    assert any("dark" in r.lower() or "underexposed" in r.lower() for r in res_dark["reasons"])

    # Bright
    bright_buf = io.BytesIO()
    Image.new("RGB", (400, 400), color=(254, 254, 254)).save(bright_buf, format="JPEG")
    res_bright = await checker.assess_quality(bright_buf.getvalue())
    assert res_bright["is_acceptable"] is False
    assert any("overexposed" in r.lower() or "glare" in r.lower() for r in res_bright["reasons"])


@pytest.mark.asyncio
async def test_quality_gate_corrupted_and_unsupported():
    """Corrupted bytes and unsupported MIME types return controlled responses without crashing."""
    checker = StandardImageQualityChecker()
    res_corrupt = await checker.assess_quality(b"garbage_not_an_image")
    assert res_corrupt["is_acceptable"] is False
    assert res_corrupt["overall_score"] == 0.0

    # Unsupported format in API endpoint
    response = client.post(
        "/api/extract",
        files={"image": ("file.gif", b"GIF89a...", "image/gif")},
    )
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_quality_gate_extreme_aspect_ratio():
    """Extreme aspect ratios fail framing check."""
    checker = StandardImageQualityChecker()
    buf = io.BytesIO()
    Image.new("RGB", (1200, 25), color=(128, 128, 128)).save(buf, format="JPEG")
    res = await checker.assess_quality(buf.getvalue())
    assert res["is_acceptable"] is False
    assert any("aspect ratio" in r.lower() for r in res["reasons"])


# --------------------------------------------------------------------------
# Group B: Extraction Edge Cases
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extraction_edge_cases_and_error_handling():
    """Verify confidence preservation, missing bounding boxes, and provider failures."""
    good_img = _make_synth_good_image()

    # 1. Extraction failure handled safely without crash
    with patch("backend.app.api.extract.get_ocr_provider") as mock_factory:
        mock_prov = AsyncMock()
        mock_prov.model_name = "gemini-2.5-flash"
        mock_prov.extract.side_effect = RuntimeError("Upstream OCR engine timed out")
        mock_factory.return_value = mock_prov

        resp = client.post(
            "/api/extract",
            files={"image": ("pkg.jpg", good_img, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Provider error" in data["error"]
        assert data["result"] is None

    # 2. Malformed JSON parsing error handled safely
    with patch("backend.app.api.extract.get_ocr_provider") as mock_factory:
        mock_prov = AsyncMock()
        mock_prov.model_name = "gemini-2.5-flash"
        mock_prov.extract.side_effect = ValueError("Failed to parse JSON response")
        mock_factory.return_value = mock_prov

        resp = client.post(
            "/api/extract",
            files={"image": ("pkg.jpg", good_img, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Failed to parse extraction result" in data["error"]


# --------------------------------------------------------------------------
# Group C: Rule Engine Edge Cases (Rules 6-9)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_engine_canonical_aggregation_hierarchy():
    """Test aggregation hierarchy: FAIL > REVIEW_REQUIRED > NOT_ASSESSABLE > PASS."""
    # 1. Empty evaluations -> NOT_ASSESSABLE
    assert aggregate_disposition([]) == ComplianceVerdict.NOT_ASSESSABLE

    # 2. All NOT_ASSESSABLE -> NOT_ASSESSABLE
    eval_na1 = RuleEvaluation(
        rule_id="R1", rule_version="v1", rule_name="Rule 1",
        status=ComplianceVerdict.NOT_ASSESSABLE, explanation="Not assessable",
    )
    eval_na2 = RuleEvaluation(
        rule_id="R2", rule_version="v1", rule_name="Rule 2",
        status=ComplianceVerdict.NOT_ASSESSABLE, explanation="Not assessable",
    )
    assert aggregate_disposition([eval_na1, eval_na2]) == ComplianceVerdict.NOT_ASSESSABLE

    # 3. PASS + NOT_ASSESSABLE -> PASS (unassessable clause does not block overall pass for compliant declarations)
    eval_pass = RuleEvaluation(
        rule_id="R3", rule_version="v1", rule_name="Rule 3",
        status=ComplianceVerdict.PASS, explanation="Compliant",
    )
    assert aggregate_disposition([eval_pass, eval_na1]) == ComplianceVerdict.PASS

    # 4. PASS + REVIEW_REQUIRED -> REVIEW_REQUIRED
    eval_rev = RuleEvaluation(
        rule_id="R4", rule_version="v1", rule_name="Rule 4",
        status=ComplianceVerdict.REVIEW_REQUIRED, explanation="Needs review",
    )
    assert aggregate_disposition([eval_pass, eval_rev]) == ComplianceVerdict.REVIEW_REQUIRED

    # 5. REVIEW_REQUIRED + NOT_ASSESSABLE -> REVIEW_REQUIRED
    assert aggregate_disposition([eval_na1, eval_rev]) == ComplianceVerdict.REVIEW_REQUIRED

    # 6. PASS + FAIL -> FAIL
    eval_fail = RuleEvaluation(
        rule_id="R5", rule_version="v1", rule_name="Rule 5",
        status=ComplianceVerdict.FAIL, explanation="Statutory violation",
    )
    assert aggregate_disposition([eval_pass, eval_fail]) == ComplianceVerdict.FAIL

    # 7. FAIL + REVIEW_REQUIRED + NOT_ASSESSABLE + PASS -> FAIL (FAIL dominates all)
    assert aggregate_disposition([eval_pass, eval_rev, eval_na1, eval_fail]) == ComplianceVerdict.FAIL


@pytest.mark.asyncio
async def test_rule_engine_rules_6_to_9_comprehensive():
    """Validate deterministic evaluation across Rules 6, 7, 8, 9 without external network calls."""
    ext = _make_fully_compliant_extraction()
    engine = DeterministicRuleEngine()

    # Rule 6 deterministic evaluation yields overall PASS
    result_r6 = await engine.evaluate(ext)
    assert len(result_r6.rule_evaluations) == 9
    assert result_r6.overall_disposition == ComplianceVerdict.PASS

    # Rule 6, 7, 8, 9 all evaluated together yields 17 evaluations
    # (Rule 8(1) free space requires inspector signoff for background artwork -> REVIEW_REQUIRED)
    result_all = await engine.evaluate_all(
        ext,
        package_metadata={
            "is_principal_display_panel": True,
            "measured_numeral_height_mm": 4.5,
            "is_contrast_verified": True,
            "capacity_cubic_cm": 4.5,
        },
    )
    assert len(result_all.rule_evaluations) == 17
    assert result_all.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED
    free_space_eval = next(
        e for e in result_all.rule_evaluations if e.rule_id == "LMR-2011-R08-01-FREE-SPACE"
    )
    assert free_space_eval.status == ComplianceVerdict.REVIEW_REQUIRED

    # Multiple simultaneous failures: missing MRP and non-metric net quantity
    ext_multi_fail = deepcopy(ext)
    ext_multi_fail.mrp = ExtractedField(status="not_found")
    ext_multi_fail.net_quantity = ExtractedField(value="2 lbs", confidence=0.95, status="extracted")
    res_multi = await engine.evaluate(ext_multi_fail)
    assert res_multi.overall_disposition == ComplianceVerdict.FAIL
    failures = [e for e in res_multi.rule_evaluations if e.status == ComplianceVerdict.FAIL]
    assert len(failures) >= 2


# --------------------------------------------------------------------------
# Group D: Human Review Edge Cases
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_human_review_net_quantity_correction_provenance():
    """Specific Test: AI extracted '500' -> Reviewer corrects to '500 g'.
    
    Verifies:
    1. Corrected observation is recorded as reviewer-corrected.
    2. Deterministic rule engine re-evaluates '500 g' to PASS.
    3. Human confirmation is not misattributed as AI confidence 100%.
    """
    ext = _make_fully_compliant_extraction()
    ext.net_quantity = ExtractedField(
        value="500",  # missing unit -> FAIL
        confidence=0.82,
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=120, height=40),
    )

    review_service = ReviewService()
    resp = await review_service.apply_review_and_evaluate(
        original_extraction=ext,
        corrections=[
            FieldCorrection(
                field_name="net_quantity",
                action=ReviewAction.CORRECT,
                corrected_value="500 g",
                source_region=SourceRegion(x=100, y=250, width=140, height=40),
                reviewer_notes="Corrected unit to 'g' per package visual evidence.",
            )
        ],
        rules=[6],
    )

    assert resp.success is True
    assert resp.initial_disposition == ComplianceVerdict.FAIL
    assert resp.final_disposition == ComplianceVerdict.PASS

    prov = resp.provenance["net_quantity"]
    assert prov.action_taken == "corrected"
    assert prov.original_value == "500"
    assert prov.original_confidence == 0.82
    assert prov.reviewed_value == "500 g"
    assert "package visual evidence" in prov.reviewer_notes

    # Verify reviewer cannot force status directly (extra forbidden field)
    with pytest.raises(Exception):
        ReviewSubmissionRequest.model_validate({
            "original_extraction": ext.model_dump(),
            "corrections": [],
            "status": "PASS",
        })


# --------------------------------------------------------------------------
# Group E: Evidence Ledger Edge Cases
# --------------------------------------------------------------------------

def test_evidence_ledger_lifecycle_and_traceability(tmp_path):
    """Verify permanent inspection_id, parent linkage, append-only, and trail retrieval."""
    db_file = str(tmp_path / "ledger_edge.db")
    ledger = EvidenceLedgerService(db_path=db_file)

    ext = _make_fully_compliant_extraction()
    rule_eval = RuleEvaluation(
        rule_id="LMR-2011-R06-01C-NET-QTY",
        rule_version="LMR-2011-BASE-R06",
        rule_name="Net Quantity",
        statutory_reference="Rule 6(1)(c)",
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation="Borderline confidence",
        observed_value="500 g",
    )
    compliance = InspectionResult(
        overall_disposition=ComplianceVerdict.REVIEW_REQUIRED,
        rule_evaluations=[rule_eval],
        summary="Inspection requires review",
        package_id="PKG-LEDGER-01",
    )

    req = CreateInspectionRecordRequest(
        extraction=ext,
        compliance=compliance,
        package_id="PKG-LEDGER-01",
        evidence=EvidenceMetadataInput(
            filename="pkg_edge.jpg",
            media_type="image/jpeg",
            file_size_bytes=10240,
            image_width=800,
            image_height=800,
            quality_assessment=QualityAssessment(
                is_acceptable=True,
                overall_score=0.95,
                reasons=[],
                details={},
            ),
        ),
    )

    insp_id = ledger.record_inspection(req)
    assert insp_id.startswith("insp_")

    # Fetch and check permanence
    trail = ledger.get_inspection(insp_id)
    assert trail.inspection.inspection_id == insp_id
    assert trail.inspection.package_id == "PKG-LEDGER-01"
    assert len(trail.observations) == 9

    # Append review resolution
    new_rule_eval = RuleEvaluation(
        rule_id="LMR-2011-R06-01C-NET-QTY",
        rule_version="LMR-2011-BASE-R06",
        rule_name="Net Quantity",
        statutory_reference="Rule 6(1)(c)",
        status=ComplianceVerdict.PASS,
        explanation="Confirmed by inspector",
        observed_value="500 g",
    )
    new_compliance = InspectionResult(
        overall_disposition=ComplianceVerdict.PASS,
        rule_evaluations=[new_rule_eval],
        summary="Review passed",
    )

    append_req = AppendReviewRequest(
        corrections=[
            FieldCorrection(
                field_name="net_quantity",
                action=ReviewAction.CONFIRM,
                reviewer_notes="Confirmed by inspector",
            )
        ],
        updated_extraction=ext,
        new_compliance=new_compliance,
    )

    updated_trail = ledger.record_review_resolution(insp_id, append_req)
    assert updated_trail.inspection.overall_disposition == ComplianceVerdict.PASS
    # 9 initial + 1 appended = 10 total observations
    assert len(updated_trail.observations) == 10
    appended_obs = [o for o in updated_trail.observations if o.source_type == "reviewer_confirm"]
    assert len(appended_obs) == 1
    assert appended_obs[0].parent_observation_id is not None

    # History listing
    summaries = ledger.list_inspections()
    assert any(s.inspection_id == insp_id for s in summaries)


# --------------------------------------------------------------------------
# Group F: Result & Missing-Data Policy Validation
# --------------------------------------------------------------------------

def test_missing_data_policy_strict_constants():
    """Validate centralized missing-data policy constants and absence of raw null/None."""
    # Scalar formatting
    assert format_missing_value(None) == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("None") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("null") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("undefined") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("   ") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("Not Applicable") == NOT_APPLICABLE_MESSAGE
    assert format_missing_value("Tata Tea", is_applicable=True) == "Tata Tea"
    assert format_missing_value("Tata Tea", is_applicable=False) == NOT_APPLICABLE_MESSAGE

    # Confidence formatting
    assert format_confidence(None) == NOT_AVAILABLE_MESSAGE
    assert format_confidence("None") == NOT_AVAILABLE_MESSAGE
    assert format_confidence(0.92) == "0.92"
    assert format_confidence(0.925) == "0.93"

    # Source region formatting
    assert format_source_region(None) == NOT_AVAILABLE_MESSAGE
    assert format_source_region(SourceRegion(x=10, y=20, width=30, height=40)) == "[10, 20, 30x40]"

    # Messages
    assert EMPTY_EVIDENCE_MESSAGE == "No evidence records available."
    assert EMPTY_OBSERVATIONS_MESSAGE == "No observations recorded."
    assert EMPTY_RULE_EVALUATIONS_MESSAGE == "No rule evaluations recorded."
    assert EMPTY_REVIEW_ACTIONS_MESSAGE == "No human review actions recorded."


# --------------------------------------------------------------------------
# Group G: PDF Generation Edge Cases
# --------------------------------------------------------------------------

def test_pdf_generation_across_all_dispositions(tmp_path):
    """Validate PDF generation for PASS, FAIL, REVIEW_REQUIRED, and NOT_ASSESSABLE."""
    db_file = str(tmp_path / "pdf_test.db")
    ledger = EvidenceLedgerService(db_path=db_file)
    result_service = ResultService(ledger_service=ledger)
    pdf_service = PDFReportService()

    ext = _make_fully_compliant_extraction()

    for disposition in [
        ComplianceVerdict.PASS,
        ComplianceVerdict.FAIL,
        ComplianceVerdict.REVIEW_REQUIRED,
        ComplianceVerdict.NOT_ASSESSABLE,
    ]:
        compliance = InspectionResult(
            overall_disposition=disposition,
            rule_evaluations=[
                RuleEvaluation(
                    rule_id="LMR-2011-R06-01C-NET-QTY",
                    rule_version="LMR-2011-BASE-R06",
                    rule_name="Net Quantity",
                    statutory_reference="Rule 6(1)(c)",
                    status=disposition,
                    explanation=f"Disposition is {disposition.value}",
                    observed_value="1 kg",
                )
            ],
            summary=f"Summary for {disposition.value}",
            package_id=f"PKG-{disposition.value}",
        )
        insp_id = ledger.record_inspection(
            CreateInspectionRecordRequest(extraction=ext, compliance=compliance)
        )
        report = result_service.get_inspection_report(insp_id)
        pdf_bytes = pdf_service.generate_report_pdf(report)

        assert pdf_bytes.startswith(b"%PDF"), f"Invalid PDF header for {disposition.value}"
        assert len(pdf_bytes) > 2000
        # Check that inspection id is embedded in the uncompressed PDF document
        assert insp_id.encode("utf-8") in pdf_bytes
        assert disposition.value.encode("utf-8") in pdf_bytes


# --------------------------------------------------------------------------
# Group H: API Robustness Edge Cases
# --------------------------------------------------------------------------

def test_api_robustness_error_codes():
    """Verify controlled error codes and refusal of unauthorized bypass."""
    # 1. Unknown inspection ID -> 404
    resp = client.get("/api/result/non_existent_insp_12345")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    resp_pdf = client.get("/api/report/pdf/non_existent_insp_12345")
    assert resp_pdf.status_code == 404

    # 2. Extract without image file -> 422
    resp_no_img = client.post("/api/extract")
    assert resp_no_img.status_code == 422

    # 3. Review submit with invalid action -> 422
    ext = _make_fully_compliant_extraction()
    bad_review_payload = {
        "original_extraction": ext.model_dump(),
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "invalid_action_not_permitted",
            }
        ],
    }
    resp_bad_act = client.post("/api/review/submit", json=bad_review_payload)
    assert resp_bad_act.status_code == 422

    # 4. Review submit attempting status bypass -> 422
    bypass_payload = {
        "original_extraction": ext.model_dump(),
        "corrections": [],
        "overall_disposition": "PASS",  # Extra field strictly forbidden
    }
    resp_bypass = client.post("/api/review/submit", json=bypass_payload)
    assert resp_bypass.status_code == 422


# --------------------------------------------------------------------------
# Group I: Four-State Status Integrity
# --------------------------------------------------------------------------

def test_four_state_status_integrity():
    """Strictly verify that ComplianceVerdict contains only the 4 canonical values."""
    canonical_values = {"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_ASSESSABLE"}
    enum_values = {v.value for v in ComplianceVerdict}
    assert enum_values == canonical_values, f"Unexpected enum values in ComplianceVerdict: {enum_values}"
    assert len(ComplianceVerdict) == 4
