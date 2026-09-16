"""Tests for Step 9 — Persistent, append-oriented Evidence Ledger (SQLite).

Verifies all 14 requirements:
1. Database initializes correctly.
2. Inspection can be created.
3. Evidence can be stored.
4. AI observations can be stored.
5. Rule evaluations can be stored.
6. Review actions can be stored.
7. Original observation remains after correction.
8. Corrected observation is recorded separately.
9. Final disposition is persisted.
10. Complete inspection can be retrieved.
11. Retrieved inspection contains the complete decision trail.
12. Transaction rollback works when persistence fails.
13. No secrets are stored.
14. Full integration with API and existing workflows.
"""

from copy import deepcopy
import os
import sqlite3
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
from backend.app.services.ledger_service import EvidenceLedgerService, sanitize_metadata


@pytest.fixture
def temp_ledger(tmp_path):
    """Fixture providing an EvidenceLedgerService with a dedicated temporary SQLite DB."""
    db_file = str(tmp_path / "test_ledger.db")
    service = EvidenceLedgerService(db_path=db_file)
    return service


@pytest.fixture
def sample_extraction():
    """Standard baseline ExtractionResult."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Wheat Flour",
            confidence=0.95,
            status="extracted",
            source_region=SourceRegion(x=50, y=50, width=200, height=40),
        ),
        manufacturer_name=ExtractedField(
            value="Agro Mills Ltd",
            confidence=0.92,
            status="extracted",
            source_region=SourceRegion(x=50, y=100, width=300, height=35),
        ),
        manufacturer_address=ExtractedField(
            value="Plot 45, GIDC Industrial Estate, Ahmedabad, Gujarat - 380001",
            confidence=0.91,
            status="extracted",
            source_region=SourceRegion(x=50, y=140, width=400, height=50),
        ),
        packer_name=ExtractedField(status="not_found"),
        importer_name=ExtractedField(status="not_found"),
        net_quantity=ExtractedField(
            value="1 kg",
            confidence=0.98,
            status="extracted",
            source_region=SourceRegion(x=100, y=250, width=120, height=40),
        ),
        mrp=ExtractedField(
            value="MRP Rs. 65.00 (incl. of all taxes)",
            confidence=0.94,
            status="extracted",
            source_region=SourceRegion(x=150, y=300, width=250, height=40),
        ),
        month_year_of_manufacture=ExtractedField(
            value="01/2025",
            confidence=0.90,
            status="extracted",
            source_region=SourceRegion(x=80, y=360, width=140, height=30),
        ),
        consumer_care_details=ExtractedField(
            value="Executive, Care Cell, care@agromills.in, 1800-222-3333, Plot 45, GIDC, Ahmedabad",
            confidence=0.93,
            status="extracted",
            source_region=SourceRegion(x=50, y=410, width=380, height=45),
        ),
    )


@pytest.fixture
def sample_compliance():
    """Standard baseline InspectionResult."""
    return InspectionResult(
        overall_disposition=ComplianceVerdict.PASS,
        rule_evaluations=[
            RuleEvaluation(
                rule_id="LMR-2011-R06-01B-PROD-NAME",
                rule_version="LMR-2011-BASE-R06",
                rule_name="Generic Commodity Name Declaration",
                status=ComplianceVerdict.PASS,
                explanation="Generic commodity name declaration is present ('Wheat Flour').",
                observed_value="Wheat Flour",
                expected_requirement="Generic/common name on principal display panel (Rule 6(1)(b)).",
                source_region=SourceRegion(x=50, y=50, width=200, height=40),
            ),
            RuleEvaluation(
                rule_id="LMR-2011-R06-01C-NET-QTY",
                rule_version="LMR-2011-BASE-R06",
                rule_name="Net Quantity Declaration",
                status=ComplianceVerdict.PASS,
                explanation="Net Quantity Declaration is valid ('1 kg') with approved metric unit 'kg'.",
                observed_value="1 kg",
                expected_requirement="Net quantity in standard metric units (Rule 6(1)(c)).",
                source_region=SourceRegion(x=100, y=250, width=120, height=40),
            ),
        ],
        summary="Disposition: PASS. All evaluated declarations pass statutory criteria.",
        package_id="PKG-WHEAT-001",
        evaluated_at="2026-09-13T12:00:00+00:00",
    )


@pytest.fixture
def sample_evidence_input():
    """Standard baseline evidence input."""
    return EvidenceMetadataInput(
        filename="flour_front_label.jpg",
        media_type="image/jpeg",
        file_size_bytes=1048576,
        image_width=1920,
        image_height=1080,
        quality_assessment=QualityAssessment(
            is_acceptable=True,
            overall_score=0.92,
            reasons=[],
            details={},
        ),
    )


# --- 1. Database initializes correctly ---


def test_database_initialization(tmp_path):
    """Test 1: Database initializes tables, indexes, and constraints correctly."""
    db_file = str(tmp_path / "init_test.db")
    service = EvidenceLedgerService(db_path=db_file)
    assert os.path.exists(db_file)

    with service._get_connection() as conn:
        cursor = conn.cursor()

        # Verify all 5 tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert {"inspections", "evidence", "observations", "rule_evaluations", "review_actions"}.issubset(tables)

        # Verify foreign keys are enabled on connections
        cursor.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1



# --- 2–5. Inspection, Evidence, AI Observations, Rule Evaluations Stored ---


def test_create_and_persist_inspection(
    temp_ledger, sample_extraction, sample_compliance, sample_evidence_input
):
    """Tests 2, 3, 4, 5: Create and store an inspection record with evidence, observations, and rules."""
    req = CreateInspectionRecordRequest(
        package_id="PKG-WHEAT-001",
        evidence=sample_evidence_input,
        extraction=sample_extraction,
        compliance=sample_compliance,
        metadata={"client_version": "1.0.0"},
    )

    insp_id = temp_ledger.record_inspection(req)
    assert insp_id.startswith("insp_")

    trail = temp_ledger.get_inspection(insp_id)

    # 2. Inspection record created
    assert trail.inspection.inspection_id == insp_id
    assert trail.inspection.overall_disposition == ComplianceVerdict.PASS
    assert trail.inspection.package_id == "PKG-WHEAT-001"

    # 3. Evidence stored
    assert len(trail.evidence) == 1
    assert trail.evidence[0].filename == "flour_front_label.jpg"
    assert trail.evidence[0].media_type == "image/jpeg"
    assert trail.evidence[0].quality_assessment.is_acceptable is True

    # 4. AI observations stored with source regions
    assert len(trail.observations) == 9
    net_obs = next(o for o in trail.observations if o.field_name == "net_quantity")
    assert net_obs.value == "1 kg"
    assert net_obs.confidence == 0.98
    assert net_obs.source_type == "ai_extraction"
    assert net_obs.source_region == SourceRegion(x=100, y=250, width=120, height=40)
    assert net_obs.parent_observation_id is None

    # 5. Rule evaluations stored with rule ID, version, and statutory reference
    assert len(trail.rule_evaluations) == 2
    net_rule = next(e for e in trail.rule_evaluations if e.rule_id == "LMR-2011-R06-01C-NET-QTY")
    assert net_rule.rule_version == "LMR-2011-BASE-R06"
    assert "Rule 6(1)(c)" in net_rule.statutory_reference
    assert net_rule.status == ComplianceVerdict.PASS
    assert net_rule.evaluation_stage == "initial"


# --- 6–9. Review actions, append observations, provenance, final disposition ---


def test_append_review_resolution_preserves_provenance(
    temp_ledger, sample_extraction, sample_compliance, sample_evidence_input
):
    """Tests 6, 7, 8, 9:
    6. Review actions stored.
    7. Original AI observation remains intact after correction.
    8. Corrected observation recorded separately with parent linkage.
    9. Final disposition updated and persisted.
    """
    # Start with an extraction where net_quantity is ambiguous "500"
    init_extraction = deepcopy(sample_extraction)
    init_extraction.net_quantity = ExtractedField(
        value="500",
        confidence=0.60,
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=100, height=35),
    )
    init_compliance = deepcopy(sample_compliance)
    init_compliance.overall_disposition = ComplianceVerdict.REVIEW_REQUIRED

    insp_id = temp_ledger.record_inspection(
        CreateInspectionRecordRequest(
            package_id="PKG-TEST-002",
            evidence=sample_evidence_input,
            extraction=init_extraction,
            compliance=init_compliance,
        )
    )

    trail_before = temp_ledger.get_inspection(insp_id)
    assert trail_before.inspection.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED
    orig_net_obs = next(o for o in trail_before.observations if o.field_name == "net_quantity")
    assert orig_net_obs.value == "500"
    assert orig_net_obs.confidence == 0.60

    # Reviewer corrects net_quantity to "500 g"
    updated_extraction = deepcopy(init_extraction)
    updated_extraction.net_quantity = ExtractedField(
        value="500 g",
        confidence=1.0,
        status="extracted",
        source_region=SourceRegion(x=100, y=250, width=130, height=35),
    )

    new_compliance = InspectionResult(
        overall_disposition=ComplianceVerdict.PASS,
        rule_evaluations=[
            RuleEvaluation(
                rule_id="LMR-2011-R06-01C-NET-QTY",
                rule_version="LMR-2011-BASE-R06",
                rule_name="Net Quantity Declaration",
                status=ComplianceVerdict.PASS,
                explanation="Net Quantity Declaration is valid ('500 g') with approved metric unit 'g'.",
                observed_value="500 g",
                expected_requirement="Net quantity in standard metric units (Rule 6(1)(c)).",
                source_region=SourceRegion(x=100, y=250, width=130, height=35),
            )
        ],
        summary="Re-evaluated post-review. Disposition: PASS.",
    )

    append_req = AppendReviewRequest(
        corrections=[
            FieldCorrection(
                field_name="net_quantity",
                action=ReviewAction.CORRECT,
                corrected_value="500 g",
                source_region=SourceRegion(x=100, y=250, width=130, height=35),
                reviewer_notes="Inspector added missing 'g' metric unit.",
            )
        ],
        updated_extraction=updated_extraction,
        new_compliance=new_compliance,
    )

    trail_after = temp_ledger.record_review_resolution(insp_id, append_req)

    # 6. Review action stored
    assert len(trail_after.review_actions) == 1
    rev = trail_after.review_actions[0]
    assert rev.field_name == "net_quantity"
    assert rev.action == ReviewAction.CORRECT
    assert rev.original_value == "500"
    assert rev.reviewed_value == "500 g"
    assert rev.reviewer_notes == "Inspector added missing 'g' metric unit."

    # 7. Original observation remains in ledger (historical preservation)
    all_net_obs = [o for o in trail_after.observations if o.field_name == "net_quantity"]
    assert len(all_net_obs) == 2  # BOTH exist!
    ai_obs = next(o for o in all_net_obs if o.source_type == "ai_extraction")
    assert ai_obs.value == "500"
    assert ai_obs.confidence == 0.60
    assert ai_obs.observation_id == orig_net_obs.observation_id

    # 8. Corrected observation recorded separately with parent linkage
    reviewed_obs = next(o for o in all_net_obs if o.source_type == "reviewer_correct")
    assert reviewed_obs.value == "500 g"
    assert reviewed_obs.confidence == 1.0
    assert reviewed_obs.parent_observation_id == orig_net_obs.observation_id  # Provenance link!

    # 9. Final disposition persisted as PASS
    assert trail_after.inspection.overall_disposition == ComplianceVerdict.PASS

    # Post-review rule evaluation is recorded with stage='post_review'
    post_evals = [e for e in trail_after.rule_evaluations if e.evaluation_stage == "post_review"]
    assert len(post_evals) == 1
    assert post_evals[0].status == ComplianceVerdict.PASS


# --- 10 & 11. Complete inspection retrieval and decision trail narrative ---


def test_complete_inspection_retrieval_and_decision_trail(
    temp_ledger, sample_extraction, sample_compliance, sample_evidence_input
):
    """Tests 10 & 11: Complete inspection can be retrieved with reconstructed decision trail."""
    insp_id = temp_ledger.record_inspection(
        CreateInspectionRecordRequest(
            package_id="PKG-TRAIL-001",
            evidence=sample_evidence_input,
            extraction=sample_extraction,
            compliance=sample_compliance,
        )
    )

    trail = temp_ledger.get_inspection(insp_id)

    # 10. Complete inspection retrieved
    assert trail.inspection.inspection_id == insp_id
    assert len(trail.evidence) == 1
    assert len(trail.observations) == 9
    assert len(trail.rule_evaluations) == 2

    # 11. Reconstructed narrative decision trail contains key audit answers
    narrative = trail.decision_trail_summary
    assert f"Inspection ID: {insp_id}" in narrative
    assert "flour_front_label.jpg" in narrative
    assert "Quality Gate: Score=0.92" in narrative
    assert "Observations Recorded: 9 declarations" in narrative
    assert "Final Disposition: PASS" in narrative


# --- 12. Transaction rollback on failure ---


def test_transaction_rollback_on_failure(temp_ledger, sample_extraction, sample_compliance):
    """Test 12: Transaction rollback works when persistence fails (no partial records)."""
    # Create invalid request with broken foreign key or simulate failure inside transaction
    class BrokenEvidenceInput:
        pass

    req = CreateInspectionRecordRequest(
        package_id="PKG-FAIL-001",
        extraction=sample_extraction,
        compliance=sample_compliance,
    )

    # Manually execute a failing transaction on the connection
    with pytest.raises(Exception):
        with temp_ledger._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspections (
                    inspection_id, created_at, overall_disposition, package_id, summary, metadata_json
                ) VALUES ('insp_should_rollback', '2026-09-13T00:00:00', 'PASS', 'PKG', 'Sum', '{}');
                """
            )
            # Intentionally cause foreign key violation
            conn.execute(
                """
                INSERT INTO observations (
                    observation_id, inspection_id, field_name, value, confidence,
                    status, source_region_json, source_type, parent_observation_id, created_at
                ) VALUES ('obs_bad', 'non_existent_foreign_key_insp', 'mrp', '10', 1.0, 'extracted', NULL, 'ai', NULL, '2026-09-13');
                """
            )

    # Confirm that 'insp_should_rollback' was NOT committed to the database
    with temp_ledger._get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM inspections WHERE inspection_id = 'insp_should_rollback';"
        ).fetchone()
        assert row is None  # Cleanly rolled back!


# --- 13. No secrets stored ---


def test_no_secrets_stored_in_database(temp_ledger, sample_extraction, sample_compliance):
    """Test 13: Secrets (API keys, authorization headers) are never stored in the database."""
    dirty_meta = {
        "client": "mobile_app",
        "GEMINI_API_KEY": "AIzaSySecretDoNotStoreMe",
        "groq_api_key": "gsk_secretKey",
        "Authorization": "Bearer sensitive_token",
        "nested_secret_token": "secret123",
    }

    clean = sanitize_metadata(dirty_meta)
    assert "GEMINI_API_KEY" not in clean
    assert "groq_api_key" not in clean
    assert "Authorization" not in clean
    assert "nested_secret_token" not in clean
    assert clean["client"] == "mobile_app"

    # Persist and inspect database raw content
    insp_id = temp_ledger.record_inspection(
        CreateInspectionRecordRequest(
            package_id="PKG-SEC-001",
            extraction=sample_extraction,
            compliance=sample_compliance,
            metadata=dirty_meta,
        )
    )

    trail = temp_ledger.get_inspection(insp_id)
    raw_meta_str = str(trail.inspection.metadata)
    assert "AIzaSy" not in raw_meta_str
    assert "gsk_secret" not in raw_meta_str
    assert "Bearer sensitive_token" not in raw_meta_str


# --- 14. REST API Endpoint Integration ---


def test_api_ledger_endpoints(sample_extraction, sample_compliance, sample_evidence_input):
    """Test 14: FastAPI endpoints POST /api/ledger/inspections and GET /api/ledger/inspections/{id}."""
    client = TestClient(app)

    payload = {
        "package_id": "PKG-API-001",
        "evidence": sample_evidence_input.model_dump(),
        "extraction": sample_extraction.model_dump(),
        "compliance": sample_compliance.model_dump(),
        "metadata": {"test_run": "api_test"},
    }

    # 1. POST /api/ledger/inspections
    create_res = client.post("/api/ledger/inspections", json=payload)
    assert create_res.status_code == 201
    create_data = create_res.json()
    insp_id = create_data["inspection"]["inspection_id"]
    assert insp_id.startswith("insp_")

    # 2. GET /api/ledger/inspections/{inspection_id}
    get_res = client.get(f"/api/ledger/inspections/{insp_id}")
    assert get_res.status_code == 200
    trail = get_res.json()
    assert trail["inspection"]["inspection_id"] == insp_id
    assert trail["inspection"]["overall_disposition"] == "PASS"
    assert len(trail["evidence"]) == 1
    assert len(trail["observations"]) == 9
    assert len(trail["rule_evaluations"]) == 2

    # 3. GET /api/ledger/inspections (list)
    list_res = client.get("/api/ledger/inspections?limit=10")
    assert list_res.status_code == 200
    summaries = list_res.json()
    assert any(s["inspection_id"] == insp_id for s in summaries)

    # 4. GET unknown inspection returns 404
    missing_res = client.get("/api/ledger/inspections/insp_unknown_xyz_999")
    assert missing_res.status_code == 404


def test_api_append_review_endpoint(sample_extraction, sample_compliance, sample_evidence_input):
    """Test POST /api/ledger/inspections/{id}/review endpoint."""
    client = TestClient(app)

    # 1. Create an inspection in REVIEW_REQUIRED state
    extraction = deepcopy(sample_extraction)
    extraction.net_quantity = ExtractedField(
        value="500",
        confidence=0.55,
        status="extracted",
    )
    compliance = deepcopy(sample_compliance)
    compliance.overall_disposition = ComplianceVerdict.REVIEW_REQUIRED

    create_res = client.post(
        "/api/ledger/inspections",
        json={
            "package_id": "PKG-REV-API-001",
            "evidence": sample_evidence_input.model_dump(),
            "extraction": extraction.model_dump(),
            "compliance": compliance.model_dump(),
        },
    )
    assert create_res.status_code == 201
    insp_id = create_res.json()["inspection"]["inspection_id"]

    # 2. Append review correction
    updated_extraction = deepcopy(extraction)
    updated_extraction.net_quantity = ExtractedField(
        value="500 g",
        confidence=1.0,
        status="extracted",
    )
    new_compliance = deepcopy(compliance)
    new_compliance.overall_disposition = ComplianceVerdict.PASS

    append_payload = {
        "corrections": [
            {
                "field_name": "net_quantity",
                "action": "correct",
                "corrected_value": "500 g",
                "reviewer_notes": "Added 'g' unit via API review.",
            }
        ],
        "updated_extraction": updated_extraction.model_dump(),
        "new_compliance": new_compliance.model_dump(),
    }

    append_res = client.post(f"/api/ledger/inspections/{insp_id}/review", json=append_payload)
    assert append_res.status_code == 200
    trail = append_res.json()

    assert trail["inspection"]["overall_disposition"] == "PASS"
    assert len(trail["review_actions"]) == 1
    assert trail["review_actions"][0]["action"] == "correct"
    assert trail["review_actions"][0]["reviewed_value"] == "500 g"


def test_canonical_status_check_constraint(temp_ledger):
    """Test that SQLite CHECK constraints strictly enforce the 4 canonical statuses.

    Attempting to insert a non-canonical status (e.g. 'WARNING', 'PENDING')
    raises sqlite3.IntegrityError.
    """
    with pytest.raises(sqlite3.IntegrityError):
        with temp_ledger._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspections (
                    inspection_id, created_at, overall_disposition, package_id, summary, metadata_json
                ) VALUES ('insp_bad_status', '2026-09-13T00:00:00', 'PENDING', 'PKG', 'Sum', '{}');
                """
            )

    with pytest.raises(sqlite3.IntegrityError):
        with temp_ledger._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspections (
                    inspection_id, created_at, overall_disposition, package_id, summary, metadata_json
                ) VALUES ('insp_bad_status_2', '2026-09-13T00:00:00', 'WARNING', 'PKG', 'Sum', '{}');
                """
            )

