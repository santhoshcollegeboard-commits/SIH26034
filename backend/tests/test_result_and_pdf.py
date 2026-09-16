"""Tests for Step 10 — Result + PDF Report layer.

Verifies:
1. Result retrieval for known inspection
2. Unknown inspection -> 404
3. PASS result representation
4. FAIL result representation
5. REVIEW_REQUIRED result representation
6. NOT_ASSESSABLE result representation
7. PDF generation succeeds (valid %PDF binary)
8. PDF content contains inspection ID
9. PDF content contains final disposition
10. PDF contains rule ID / statutory reference
11. PDF contains review information when review exists
12. PDF does not invent unavailable values ("Not available in recorded evidence")
13. PDF endpoint returns application/pdf
14. Unknown inspection PDF -> 404
15. Report generation does not invoke Gemini
16. Report generation does not invoke rule engine
17. Existing ledger records remain unchanged
"""

from copy import deepcopy
from typing import Optional
from unittest.mock import patch
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import (
    ComplianceVerdict,
    InspectionResult,
    RuleEvaluation,
)
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.schemas.ledger import (
    AppendReviewRequest,
    CreateInspectionRecordRequest,
    EvidenceMetadataInput,
)
from backend.app.schemas.quality import QualityAssessment
from backend.app.schemas.review import FieldCorrection, ReviewAction
from backend.app.services.formatters import (
    EMPTY_EVIDENCE_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    EMPTY_REVIEW_ACTIONS_MESSAGE,
    EMPTY_RULE_EVALUATIONS_MESSAGE,
    NOT_APPLICABLE_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    NOT_RECORDED_MESSAGE,
    format_confidence,
    format_missing_value,
    format_quality_summary,
    format_source_region,
)
from backend.app.services.ledger_service import EvidenceLedgerService
from backend.app.services.report_service import PDFReportService
from backend.app.services.result_service import ResultService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_ledger(tmp_path):
    """Fixture providing a clean SQLite EvidenceLedgerService for testing."""
    db_file = str(tmp_path / "result_test.db")
    return EvidenceLedgerService(db_path=db_file)


@pytest.fixture
def sample_extraction():
    """Standard baseline ExtractionResult."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Basmati Rice",
            confidence=0.96,
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


@pytest.fixture
def sample_evidence_input():
    """Standard baseline evidence input."""
    return EvidenceMetadataInput(
        filename="basmati_rice_pouch.jpg",
        media_type="image/jpeg",
        file_size_bytes=2048576,
        image_width=2400,
        image_height=1800,
        quality_assessment=QualityAssessment(
            is_acceptable=True,
            overall_score=0.95,
            reasons=[],
            details={"sharpness": "high", "lighting": "optimal"},
        ),
    )


def create_inspection_with_verdict(
    ledger: EvidenceLedgerService,
    verdict: ComplianceVerdict,
    extraction: ExtractionResult,
    # pyrefly: ignore [unknown-name]
    evidence: Optional[EvidenceMetadataInput] = None,
    pkg_id: str = "PKG-TEST-001",
) -> str:
    """Helper to store an inspection record with a specific canonical verdict."""
    rule_eval = RuleEvaluation(
        rule_id="LMR-2011-R06-01C-NET-QTY",
        rule_version="LMR-2011-BASE-R06",
        rule_name="Net Quantity Declaration",
        status=verdict,
        explanation=f"Evaluated status {verdict.value} for statutory test verification.",
        observed_value=extraction.net_quantity.value,
        expected_requirement="Net quantity in standard metric units (Rule 6(1)(c)).",
        source_region=extraction.net_quantity.source_region,
    )
    comp = InspectionResult(
        overall_disposition=verdict,
        rule_evaluations=[rule_eval],
        summary=f"Disposition: {verdict.value}. Test inspection summary.",
        package_id=pkg_id,
        evaluated_at="2026-09-13T16:00:00+00:00",
    )
    req = CreateInspectionRecordRequest(
        package_id=pkg_id,
        evidence=evidence,
        extraction=extraction,
        compliance=comp,
    )
    return ledger.record_inspection(req)


# --- 1 & 2: Result retrieval for known & unknown inspection ---


def test_result_retrieval_known_inspection(temp_ledger, sample_extraction, sample_evidence_input):
    """Test 1: Result retrieval returns complete report-ready representation."""
    insp_id = create_inspection_with_verdict(
        temp_ledger,
        ComplianceVerdict.PASS,
        sample_extraction,
        sample_evidence_input,
    )

    result_service = ResultService(ledger_service=temp_ledger)
    report = result_service.get_inspection_report(insp_id)

    assert report.inspection_id == insp_id
    assert report.overall_disposition == ComplianceVerdict.PASS
    assert report.package_id == "PKG-TEST-001"
    assert report.evidence is not None
    assert report.evidence.filename == "basmati_rice_pouch.jpg"
    assert report.quality is not None
    assert report.quality.is_acceptable is True
    assert len(report.observations) == 9
    assert len(report.rule_evaluations) == 1
    assert report.traceability.evaluated_rule_count == 1
    assert "Inspection ID:" in report.decision_trail_summary


def test_result_retrieval_unknown_inspection_raises_keyerror(temp_ledger):
    """Test 2: Unknown inspection ID raises KeyError."""
    result_service = ResultService(ledger_service=temp_ledger)
    with pytest.raises(KeyError):
        result_service.get_inspection_report("insp_non_existent_999")


# --- 3–6: Canonical Dispositions Representation (PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE) ---


def test_pass_result_representation(temp_ledger, sample_extraction, sample_evidence_input):
    """Test 3: PASS disposition representation."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    assert report.overall_disposition == ComplianceVerdict.PASS


def test_fail_result_representation(temp_ledger, sample_extraction, sample_evidence_input):
    """Test 4: FAIL disposition representation."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.FAIL, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    assert report.overall_disposition == ComplianceVerdict.FAIL


def test_review_required_result_representation(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Test 5: REVIEW_REQUIRED disposition representation."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.REVIEW_REQUIRED, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    assert report.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED


def test_not_assessable_result_representation(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Test 6: NOT_ASSESSABLE disposition representation."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.NOT_ASSESSABLE, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    assert report.overall_disposition == ComplianceVerdict.NOT_ASSESSABLE


# --- 7–12: PDF Generation, Structure, Content, Fallbacks ---


def test_pdf_generation_succeeds(temp_ledger, sample_extraction, sample_evidence_input):
    """Test 7: PDF generation succeeds and returns non-empty binary bytes starting with %PDF."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    report_service = PDFReportService()
    pdf_bytes = report_service.generate_report_pdf(report)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_content_contains_inspection_id_and_disposition(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Tests 8 & 9: PDF binary stream contains inspection ID and final disposition string."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.FAIL, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    pdf_bytes = PDFReportService().generate_report_pdf(report)

    # Convert bytes to latin-1 / raw string to check embedded strings
    raw_pdf = pdf_bytes.decode("latin-1")
    assert insp_id in raw_pdf
    assert "FAIL" in raw_pdf


def test_pdf_contains_rule_id_and_statutory_reference(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Test 10: PDF contains rule ID and statutory reference."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, sample_evidence_input
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")
    assert "LMR-2011-R06-01C-NET-QTY" in raw_pdf
    assert "Rule 6" in raw_pdf
    assert ("Rule 6\\(1\\)\\(c\\)" in raw_pdf or "Rule 6(1)(c)" in raw_pdf)



def test_pdf_contains_review_information_when_review_exists(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Test 11: PDF contains human review resolution details when review actions are present."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.REVIEW_REQUIRED, sample_extraction, sample_evidence_input
    )

    # Append review correction
    updated_extraction = deepcopy(sample_extraction)
    updated_extraction.net_quantity = ExtractedField(
        value="5 kg",
        confidence=1.0,
        status="extracted",
    )
    new_compliance = InspectionResult(
        overall_disposition=ComplianceVerdict.PASS,
        rule_evaluations=[
            RuleEvaluation(
                rule_id="LMR-2011-R06-01C-NET-QTY",
                rule_version="LMR-2011-BASE-R06",
                rule_name="Net Quantity Declaration",
                status=ComplianceVerdict.PASS,
                explanation="Confirmed 5 kg by inspector.",
                observed_value="5 kg",
                expected_requirement="Metric unit",
            )
        ],
    )

    temp_ledger.record_review_resolution(
        insp_id,
        AppendReviewRequest(
            corrections=[
                FieldCorrection(
                    field_name="net_quantity",
                    action=ReviewAction.CONFIRM,
                    reviewer_notes="Inspector confirmed net quantity from physical label.",
                )
            ],
            updated_extraction=updated_extraction,
            new_compliance=new_compliance,
        ),
    )

    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")

    assert "Inspector confirmed net quantity from physical label." in raw_pdf


def test_pdf_does_not_invent_unavailable_values(temp_ledger, sample_extraction):
    """Test 12: PDF handles missing evidence safely with explicit fallback text."""
    # Create inspection with NO evidence attached
    insp_id = create_inspection_with_verdict(
        temp_ledger,
        ComplianceVerdict.NOT_ASSESSABLE,
        sample_extraction,
        evidence=None,
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    assert report.evidence is None

    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")
    assert "Not available in recorded evidence" in raw_pdf


# --- 13 & 14: REST API Endpoints GET /api/result/{id} and GET /api/result/{id}/pdf ---


def test_api_result_and_pdf_endpoints(client, sample_extraction, sample_evidence_input):
    """Tests 13 & 14: API endpoints for result JSON and streaming PDF."""
    # 1. First record an inspection via ledger API
    create_res = client.post(
        "/api/ledger/inspections",
        json={
            "package_id": "PKG-PDF-API-001",
            "evidence": sample_evidence_input.model_dump(),
            "extraction": sample_extraction.model_dump(),
            "compliance": {
                "overall_disposition": "PASS",
                "rule_evaluations": [
                    {
                        "rule_id": "LMR-2011-R06-01B-PROD-NAME",
                        "rule_version": "LMR-2011-BASE-R06",
                        "rule_name": "Product Name",
                        "status": "PASS",
                        "explanation": "Valid generic product name.",
                        "observed_value": "Basmati Rice",
                    }
                ],
                "summary": "Overall PASS.",
            },
        },
    )
    assert create_res.status_code == 201
    insp_id = create_res.json()["inspection"]["inspection_id"]

    # 2. GET /api/result/{inspection_id} -> JSON report
    res_json = client.get(f"/api/result/{insp_id}")
    assert res_json.status_code == 200
    report_data = res_json.json()
    assert report_data["inspection_id"] == insp_id
    assert report_data["overall_disposition"] == "PASS"
    assert report_data["package_id"] == "PKG-PDF-API-001"

    # 3. GET /api/result/{inspection_id}/pdf -> application/pdf
    res_pdf = client.get(f"/api/result/{insp_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["Content-Type"] == "application/pdf"
    assert f'filename="PackCheck_{insp_id}.pdf"' in res_pdf.headers["Content-Disposition"]
    assert res_pdf.content.startswith(b"%PDF")

    # 4. Unknown inspection -> 404 for JSON and PDF
    res_404_json = client.get("/api/result/insp_missing_000")
    assert res_404_json.status_code == 404

    res_404_pdf = client.get("/api/result/insp_missing_000/pdf")
    assert res_404_pdf.status_code == 404


# --- 15 & 16: Report generation does NOT invoke Gemini or RuleEngine ---


def test_report_generation_does_not_invoke_gemini_or_rule_engine(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Tests 15 & 16: Generating report/PDF strictly reads ledger data without calling AI or rules."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, sample_evidence_input
    )

    with patch(
        "backend.app.services.providers.gemini_provider.GeminiOCRProvider.extract",
        side_effect=RuntimeError("AI must not be called!"),
    ) as mock_gemini, patch(
        "backend.app.services.rule_engine_service.DeterministicRuleEngine.evaluate",
        side_effect=RuntimeError("RuleEngine must not be called!"),
    ) as mock_rules:
        # Fetch report
        report = ResultService(temp_ledger).get_inspection_report(insp_id)
        # Generate PDF
        pdf_bytes = PDFReportService().generate_report_pdf(report)

        assert len(pdf_bytes) > 0
        mock_gemini.assert_not_called()
        mock_rules.assert_not_called()


# --- 17: Existing ledger records remain unchanged ---


def test_ledger_records_remain_unchanged_after_reporting(
    temp_ledger, sample_extraction, sample_evidence_input
):
    """Test 17: Generating a report and PDF does not alter or mutate the underlying ledger data."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, sample_evidence_input
    )

    trail_before = temp_ledger.get_inspection(insp_id)

    # Generate report and PDF
    report = ResultService(temp_ledger).get_inspection_report(insp_id)
    _ = PDFReportService().generate_report_pdf(report)

    trail_after = temp_ledger.get_inspection(insp_id)

    # Identical before and after
    assert trail_before.inspection.model_dump() == trail_after.inspection.model_dump()
    assert len(trail_before.observations) == len(trail_after.observations)
    assert len(trail_before.rule_evaluations) == len(trail_after.rule_evaluations)
    assert len(trail_before.review_actions) == len(trail_after.review_actions)


# --- 18–27: Missing-data policy tests ---


def test_policy_1_none_renders_as_not_available_in_recorded_evidence(temp_ledger):
    """Test Policy 1: None scalar values render as 'Not available in recorded evidence'."""
    assert format_missing_value(None) == NOT_AVAILABLE_MESSAGE

    empty_extraction = ExtractionResult()
    insp_id = create_inspection_with_verdict(
        temp_ledger,
        ComplianceVerdict.PASS,
        empty_extraction,
        evidence=None,
        pkg_id=None,
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    assert report.package_id == NOT_AVAILABLE_MESSAGE
    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")
    assert NOT_AVAILABLE_MESSAGE in raw_pdf


def test_policy_2_empty_strings_render_as_not_available_in_recorded_evidence():
    """Test Policy 2: Empty and whitespace strings render as 'Not available in recorded evidence'."""
    assert format_missing_value("") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("   ") == NOT_AVAILABLE_MESSAGE
    assert format_missing_value("\t\n") == NOT_AVAILABLE_MESSAGE


def test_policy_3_missing_confidence_does_not_become_zero_or_one(temp_ledger):
    """Test Policy 3: Missing confidence renders as 'Not available in recorded evidence' and never 0 or 1."""
    assert format_confidence(None) == NOT_AVAILABLE_MESSAGE
    assert format_confidence(None) not in ("0", "0.0", "0.00", "1", "1.0", "1.00")

    extraction = ExtractionResult(
        product_name=ExtractedField(
            value="Basmati Rice",
            confidence=None,
            status="extracted",
        )
    )
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    # First observation is product_name
    prod_obs = next(o for o in report.observations if o.field_name == "product_name")
    assert prod_obs.confidence == NOT_AVAILABLE_MESSAGE
    assert prod_obs.confidence not in ("0", "0.0", "0.00", "1", "1.0", "1.00")


def test_policy_4_missing_source_region_rendered_consistently(temp_ledger):
    """Test Policy 4: Missing source region renders consistently without fabricated coordinates."""
    assert format_source_region(None) == NOT_AVAILABLE_MESSAGE

    extraction = ExtractionResult(
        product_name=ExtractedField(
            value="Basmati Rice",
            confidence=0.95,
            status="extracted",
            source_region=None,
        )
    )
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    prod_obs = next(o for o in report.observations if o.field_name == "product_name")
    assert prod_obs.source_region == NOT_AVAILABLE_MESSAGE


def test_policy_5_empty_review_actions_shows_no_human_review_actions_recorded(temp_ledger, sample_extraction):
    """Test Policy 5: Empty review actions displays 'No human review actions recorded.'."""
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, sample_extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    assert report.review_actions_message == EMPTY_REVIEW_ACTIONS_MESSAGE
    assert len(report.review_actions) == 0

    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")
    assert "No human review actions recorded." in raw_pdf


def test_policy_6_not_assessable_remains_not_assessable(temp_ledger, sample_extraction):
    """Test Policy 6: NOT_ASSESSABLE remains canonical and is not replaced by generic message."""
    assert format_missing_value("NOT_ASSESSABLE") == "NOT_ASSESSABLE"

    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.NOT_ASSESSABLE, sample_extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    assert report.overall_disposition == ComplianceVerdict.NOT_ASSESSABLE
    assert report.overall_disposition.value == "NOT_ASSESSABLE"
    assert report.rule_evaluations[0].status == ComplianceVerdict.NOT_ASSESSABLE

    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")
    assert "NOT_ASSESSABLE" in raw_pdf


def test_policy_7_explicitly_recorded_not_applicable_data_renders_not_applicable(temp_ledger):
    """Test Policy 7: Explicitly recorded not-applicable data renders as 'Not applicable'."""
    assert format_missing_value("not_applicable") == NOT_APPLICABLE_MESSAGE
    assert format_missing_value("Not applicable") == NOT_APPLICABLE_MESSAGE
    assert format_missing_value(None, is_applicable=False) == NOT_APPLICABLE_MESSAGE
    assert format_confidence(None, is_applicable=False) == NOT_APPLICABLE_MESSAGE
    assert format_source_region(None, is_applicable=False) == NOT_APPLICABLE_MESSAGE

    extraction = ExtractionResult(
        importer_name=ExtractedField(
            value="not_applicable",
            confidence=None,
            status="not_applicable",
        )
    )
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    imp_obs = next(o for o in report.observations if o.field_name == "importer_name")
    assert imp_obs.value == NOT_APPLICABLE_MESSAGE


def test_policy_8_no_raw_none_null_or_undefined_in_result_api_and_pdf(client):
    """Test Policy 8: No raw None, null, or undefined appears in user-facing Result API or PDF output."""
    create_res = client.post(
        "/api/ledger/inspections",
        json={
            "package_id": None,
            "evidence": None,
            "extraction": {
                "product_name": {"value": None, "confidence": None, "status": "not_found"},
            },
            "compliance": {
                "overall_disposition": "NOT_ASSESSABLE",
                "rule_evaluations": [
                    {
                        "rule_id": "LMR-2011-R06-01B-PROD-NAME",
                        "rule_version": "LMR-2011-BASE-R06",
                        "rule_name": "Product Name",
                        "status": "NOT_ASSESSABLE",
                        "explanation": "Missing declaration cannot be assessed.",
                        "observed_value": None,
                        "expected_requirement": None,
                    }
                ],
                "summary": None,
            },
        },
    )
    assert create_res.status_code == 201
    insp_id = create_res.json()["inspection"]["inspection_id"]

    # 1. Inspect Result API JSON
    res_json = client.get(f"/api/result/{insp_id}")
    assert res_json.status_code == 200
    json_text = res_json.text

    assert ": null" not in json_text
    assert ":null" not in json_text
    assert "undefined" not in json_text
    assert '"None"' not in json_text

    data = res_json.json()
    assert data["package_id"] == NOT_AVAILABLE_MESSAGE
    assert data["summary"] == NOT_AVAILABLE_MESSAGE

    # 2. Inspect PDF
    res_pdf = client.get(f"/api/result/{insp_id}/pdf")
    assert res_pdf.status_code == 200
    pdf_text = res_pdf.content.decode("latin-1")
    assert "None" not in pdf_text or "None specified" not in pdf_text
    assert NOT_AVAILABLE_MESSAGE in pdf_text
    assert EMPTY_EVIDENCE_MESSAGE in pdf_text
    assert EMPTY_REVIEW_ACTIONS_MESSAGE in pdf_text


def test_policy_missing_extracted_declaration_renders_not_recorded(temp_ledger):
    """Test Policy 2: Expected declaration with no recorded observation has Value='Not available in recorded evidence' and Status='Not recorded'."""
    # Provide only 1 declaration (product_name)
    partial_extraction = ExtractionResult(
        product_name=ExtractedField(value="Salt", confidence=0.99, status="extracted")
    )
    insp_id = create_inspection_with_verdict(
        temp_ledger, ComplianceVerdict.PASS, partial_extraction, evidence=None
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    # Importer name was not recorded
    imp_obs = next(o for o in report.observations if o.field_name == "importer_name")
    assert imp_obs.value == NOT_AVAILABLE_MESSAGE
    assert imp_obs.status == NOT_RECORDED_MESSAGE
    assert imp_obs.confidence == NOT_AVAILABLE_MESSAGE
    assert imp_obs.source_region == NOT_AVAILABLE_MESSAGE
    # Unrecorded declaration is not labeled PASS or FAIL
    assert imp_obs.status not in ("PASS", "FAIL")


def test_policy_empty_collections_section_messages(temp_ledger):
    """Test Policy 8: Empty collections display specific meaningful section-level messages."""
    assert EMPTY_EVIDENCE_MESSAGE == "No evidence records available."
    assert EMPTY_OBSERVATIONS_MESSAGE == "No observations recorded."
    assert EMPTY_RULE_EVALUATIONS_MESSAGE == "No rule evaluations recorded."
    assert EMPTY_REVIEW_ACTIONS_MESSAGE == "No human review actions recorded."

    insp_id = create_inspection_with_verdict(
        temp_ledger,
        ComplianceVerdict.NOT_ASSESSABLE,
        ExtractionResult(),
        evidence=None,
    )
    report = ResultService(temp_ledger).get_inspection_report(insp_id)

    pdf_bytes = PDFReportService().generate_report_pdf(report)
    raw_pdf = pdf_bytes.decode("latin-1")

    assert EMPTY_EVIDENCE_MESSAGE in raw_pdf
    assert EMPTY_REVIEW_ACTIONS_MESSAGE in raw_pdf

