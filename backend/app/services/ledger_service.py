"""Evidence Ledger Service for Legal Metrology inspections (SQLite).

Preserves the complete auditable chain:
Evidence -> Observation -> Rule Evaluation -> Review Action -> Final Disposition

Answering:
"What evidence and decision path produced this inspection result?"

Features:
- ACID transactional integrity (automatic rollback on failure)
- Append-oriented audit design (historical observations are never overwritten)
- Parent-child observation linkage for reviewer corrections
- Full rule version and statutory clause traceability
- Zero secret storage
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional
from uuid import uuid4

from backend.app.core.config import get_settings
from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.ledger import (
    AppendReviewRequest,
    CreateInspectionRecordRequest,
    EvidenceRecord,
    FullInspectionTrailResponse,
    InspectionRecordSummary,
    ObservationRecord,
    ReviewActionRecord,
    RuleEvaluationRecord,
)
from backend.app.schemas.quality import QualityAssessment
from backend.app.schemas.review import ReviewAction
from backend.app.services.review_service import RULE_METADATA_MAP

logger = logging.getLogger(__name__)

# Keys to sanitize from metadata to prevent storing secrets
SENSITIVE_KEYS = {
    "api_key",
    "secret",
    "token",
    "gemini_api_key",
    "groq_api_key",
    "authorization",
    "password",
}


def sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize metadata by removing any credentials or secrets."""
    if not meta:
        return {}
    clean: Dict[str, Any] = {}
    for k, v in meta.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            continue
        clean[k] = v
    return clean


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or path exposure."""
    base = os.path.basename(filename).strip()
    return base or "unnamed_package_image.jpg"


class EvidenceLedgerService:
    """Service managing the persistent SQLite Evidence Ledger."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path is not None:
            self.db_path = db_path
        else:
            self.db_path = get_settings().SQLITE_DB_PATH

        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an SQLite connection with WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create relational tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            # 1. inspections table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inspections (
                    inspection_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    overall_disposition TEXT NOT NULL CHECK (
                        overall_disposition IN ('PASS', 'FAIL', 'REVIEW_REQUIRED', 'NOT_ASSESSABLE')
                    ),
                    package_id TEXT,
                    summary TEXT,
                    metadata_json TEXT
                );
                """
            )

            # 2. evidence table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    inspection_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    image_width INTEGER,
                    image_height INTEGER,
                    quality_assessment_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id) ON DELETE CASCADE
                );
                """
            )

            # 3. observations table (append-oriented)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    inspection_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    value TEXT,
                    confidence REAL,
                    status TEXT NOT NULL,
                    source_region_json TEXT,
                    source_type TEXT NOT NULL,
                    parent_observation_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_observation_id) REFERENCES observations (observation_id)
                );
                """
            )

            # 4. rule_evaluations table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rule_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    inspection_id TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    rule_version TEXT NOT NULL,
                    rule_name TEXT NOT NULL,
                    statutory_reference TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('PASS', 'FAIL', 'REVIEW_REQUIRED', 'NOT_ASSESSABLE')
                    ),
                    observed_value TEXT,
                    expected_requirement TEXT,
                    explanation TEXT NOT NULL,
                    source_region_json TEXT,
                    evidence_reference TEXT,
                    evaluation_stage TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id) ON DELETE CASCADE
                );
                """
            )

            # 5. review_actions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_actions (
                    review_id TEXT PRIMARY KEY,
                    inspection_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    original_value TEXT,
                    reviewed_value TEXT,
                    original_confidence REAL,
                    source_region_before_json TEXT,
                    source_region_after_json TEXT,
                    reviewer_notes TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id) ON DELETE CASCADE
                );
                """
            )

            # Performance and query indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_insp ON evidence(inspection_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_insp ON observations(inspection_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_parent ON observations(parent_observation_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_eval_insp ON rule_evaluations(inspection_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rev_insp ON review_actions(inspection_id);")

    def record_inspection(
        self,
        request: CreateInspectionRecordRequest,
        inspection_id: Optional[str] = None,
    ) -> str:
        """Atomically persist a complete inspection record into the ledger.

        Rolls back all writes if any insert fails.
        """
        insp_id = inspection_id or f"insp_{uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_meta = sanitize_metadata(request.metadata)

        # Include rule engine version info if not provided
        if "rule_engine" not in clean_meta:
            clean_meta["rule_engine"] = "DeterministicRuleEngine-v1.0"
        if request.compliance.evaluated_at:
            clean_meta["evaluated_at"] = request.compliance.evaluated_at

        with self._get_connection() as conn:
            # 1. Insert into inspections
            conn.execute(
                """
                INSERT INTO inspections (
                    inspection_id, created_at, overall_disposition, package_id, summary, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    insp_id,
                    now_iso,
                    request.compliance.overall_disposition.value,
                    request.package_id or request.compliance.package_id,
                    request.compliance.summary,
                    json.dumps(clean_meta),
                ),
            )

            # 2. Insert into evidence if provided
            if request.evidence:
                ev_id = f"ev_{uuid4().hex[:12]}"
                safe_fname = sanitize_filename(request.evidence.filename)
                qa_json = (
                    request.evidence.quality_assessment.model_dump_json()
                    if request.evidence.quality_assessment
                    else None
                )
                conn.execute(
                    """
                    INSERT INTO evidence (
                        evidence_id, inspection_id, filename, media_type, file_size_bytes,
                        image_width, image_height, quality_assessment_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        ev_id,
                        insp_id,
                        safe_fname,
                        request.evidence.media_type,
                        request.evidence.file_size_bytes,
                        request.evidence.image_width,
                        request.evidence.image_height,
                        qa_json,
                        now_iso,
                    ),
                )

            # 3. Insert initial observations (AI extraction)
            field_obs_ids: Dict[str, str] = {}
            for field_name in [
                "product_name",
                "manufacturer_name",
                "manufacturer_address",
                "packer_name",
                "importer_name",
                "net_quantity",
                "mrp",
                "month_year_of_manufacture",
                "consumer_care_details",
            ]:
                field_obj = getattr(request.extraction, field_name, None)
                if field_obj is not None:
                    obs_id = f"obs_{uuid4().hex[:12]}"
                    field_obs_ids[field_name] = obs_id
                    sr_json = (
                        field_obj.source_region.model_dump_json()
                        if field_obj.source_region
                        else None
                    )
                    conn.execute(
                        """
                        INSERT INTO observations (
                            observation_id, inspection_id, field_name, value, confidence,
                            status, source_region_json, source_type, parent_observation_id, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            obs_id,
                            insp_id,
                            field_name,
                            field_obj.value,
                            field_obj.confidence,
                            field_obj.status,
                            sr_json,
                            "ai_extraction",
                            None,
                            now_iso,
                        ),
                    )

            # 4. Insert initial rule evaluations
            for eval_item in request.compliance.rule_evaluations:
                eval_id = f"eval_{uuid4().hex[:12]}"
                meta_item = RULE_METADATA_MAP.get(eval_item.rule_id, {})
                statutory_ref = meta_item.get(
                    "statutory_reference",
                    f"Legal Metrology (Packaged Commodities) Rules, 2011 — {eval_item.rule_id}",
                )
                sr_json = (
                    eval_item.source_region.model_dump_json()
                    if eval_item.source_region
                    else None
                )
                obs_val_str = (
                    str(eval_item.observed_value)
                    if eval_item.observed_value is not None
                    else None
                )
                conn.execute(
                    """
                    INSERT INTO rule_evaluations (
                        evaluation_id, inspection_id, rule_id, rule_version, rule_name,
                        statutory_reference, status, observed_value, expected_requirement,
                        explanation, source_region_json, evidence_reference, evaluation_stage, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        eval_id,
                        insp_id,
                        eval_item.rule_id,
                        eval_item.rule_version,
                        eval_item.rule_name,
                        statutory_ref,
                        eval_item.status.value,
                        obs_val_str,
                        eval_item.expected_requirement,
                        eval_item.explanation,
                        sr_json,
                        eval_item.evidence_reference,
                        "initial",
                        now_iso,
                    ),
                )

            # 5. If initial review corrections are supplied directly
            if request.corrections:
                for corr in request.corrections:
                    rev_id = f"rev_{uuid4().hex[:12]}"
                    parent_id = field_obs_ids.get(corr.field_name)
                    orig_field = getattr(request.extraction, corr.field_name, None)
                    orig_val = orig_field.value if orig_field else None
                    orig_conf = orig_field.confidence if orig_field else None
                    sr_before = (
                        orig_field.source_region.model_dump_json()
                        if orig_field and orig_field.source_region
                        else None
                    )
                    sr_after = (
                        corr.source_region.model_dump_json() if corr.source_region else sr_before
                    )

                    rev_val: Optional[str] = None
                    if corr.action == ReviewAction.CORRECT:
                        rev_val = corr.corrected_value
                    elif corr.action == ReviewAction.CONFIRM:
                        rev_val = orig_val

                    conn.execute(
                        """
                        INSERT INTO review_actions (
                            review_id, inspection_id, field_name, action, original_value,
                            reviewed_value, original_confidence, source_region_before_json,
                            source_region_after_json, reviewer_notes, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            rev_id,
                            insp_id,
                            corr.field_name,
                            corr.action.value,
                            orig_val,
                            rev_val,
                            orig_conf,
                            sr_before,
                            sr_after,
                            corr.reviewer_notes,
                            now_iso,
                        ),
                    )

        return insp_id

    def record_review_resolution(
        self,
        inspection_id: str,
        request: AppendReviewRequest,
    ) -> FullInspectionTrailResponse:
        """Append human reviewer resolutions and post-review re-evaluations to an existing inspection.

        Preserves historical AI observations and links new observations to their parents.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check existence of inspection
            row = conn.execute(
                "SELECT inspection_id FROM inspections WHERE inspection_id = ?;",
                (inspection_id,),
            ).fetchone()
            if not row:
                raise KeyError(f"Inspection '{inspection_id}' not found in Evidence Ledger.")

            # Fetch latest observation IDs for each field to set as parent_observation_id
            obs_rows = conn.execute(
                """
                SELECT observation_id, field_name, value, confidence, source_region_json
                FROM observations
                WHERE inspection_id = ?
                ORDER BY created_at ASC;
                """,
                (inspection_id,),
            ).fetchall()

            latest_obs_map: Dict[str, sqlite3.Row] = {}
            for r in obs_rows:
                latest_obs_map[r["field_name"]] = r

            # 1. Record each review action and new append observation
            for corr in request.corrections:
                rev_id = f"rev_{uuid4().hex[:12]}"
                parent_row = latest_obs_map.get(corr.field_name)
                parent_id = parent_row["observation_id"] if parent_row else None
                orig_val = parent_row["value"] if parent_row else None
                orig_conf = parent_row["confidence"] if parent_row else None
                sr_before = parent_row["source_region_json"] if parent_row else None

                reviewed_val: Optional[str] = None
                reviewed_conf = 1.0
                reviewed_status = "extracted"

                if corr.action == ReviewAction.CORRECT:
                    reviewed_val = corr.corrected_value
                elif corr.action == ReviewAction.CONFIRM:
                    reviewed_val = orig_val
                elif corr.action == ReviewAction.MARK_UNASSESSABLE:
                    reviewed_val = None
                    reviewed_conf = 0.0
                    reviewed_status = "unreadable"

                sr_after = (
                    corr.source_region.model_dump_json()
                    if corr.source_region
                    else sr_before
                )

                # Insert into review_actions
                conn.execute(
                    """
                    INSERT INTO review_actions (
                        review_id, inspection_id, field_name, action, original_value,
                        reviewed_value, original_confidence, source_region_before_json,
                        source_region_after_json, reviewer_notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        rev_id,
                        inspection_id,
                        corr.field_name,
                        corr.action.value,
                        orig_val,
                        reviewed_val,
                        orig_conf,
                        sr_before,
                        sr_after,
                        corr.reviewer_notes,
                        now_iso,
                    ),
                )

                # Append new observation pointing to parent
                new_obs_id = f"obs_{uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO observations (
                        observation_id, inspection_id, field_name, value, confidence,
                        status, source_region_json, source_type, parent_observation_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        new_obs_id,
                        inspection_id,
                        corr.field_name,
                        reviewed_val,
                        reviewed_conf,
                        reviewed_status,
                        sr_after,
                        f"reviewer_{corr.action.value}",
                        parent_id,
                        now_iso,
                    ),
                )

            # 2. Append new post-review rule evaluations
            for eval_item in request.new_compliance.rule_evaluations:
                eval_id = f"eval_{uuid4().hex[:12]}"
                meta_item = RULE_METADATA_MAP.get(eval_item.rule_id, {})
                statutory_ref = meta_item.get(
                    "statutory_reference",
                    f"Legal Metrology (Packaged Commodities) Rules, 2011 — {eval_item.rule_id}",
                )
                sr_json = (
                    eval_item.source_region.model_dump_json()
                    if eval_item.source_region
                    else None
                )
                obs_val_str = (
                    str(eval_item.observed_value)
                    if eval_item.observed_value is not None
                    else None
                )
                conn.execute(
                    """
                    INSERT INTO rule_evaluations (
                        evaluation_id, inspection_id, rule_id, rule_version, rule_name,
                        statutory_reference, status, observed_value, expected_requirement,
                        explanation, source_region_json, evidence_reference, evaluation_stage, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        eval_id,
                        inspection_id,
                        eval_item.rule_id,
                        eval_item.rule_version,
                        eval_item.rule_name,
                        statutory_ref,
                        eval_item.status.value,
                        obs_val_str,
                        eval_item.expected_requirement,
                        eval_item.explanation,
                        sr_json,
                        eval_item.evidence_reference,
                        "post_review",
                        now_iso,
                    ),
                )

            # 3. Update overall inspection disposition
            conn.execute(
                """
                UPDATE inspections
                SET overall_disposition = ?, summary = ?
                WHERE inspection_id = ?;
                """,
                (
                    request.new_compliance.overall_disposition.value,
                    request.new_compliance.summary,
                    inspection_id,
                ),
            )

        return self.get_inspection(inspection_id)

    def get_inspection(self, inspection_id: str) -> FullInspectionTrailResponse:
        """Retrieve complete auditable decision trail for an inspection."""
        with self._get_connection() as conn:
            # 1. Fetch inspection header
            insp_row = conn.execute(
                "SELECT * FROM inspections WHERE inspection_id = ?;",
                (inspection_id,),
            ).fetchone()
            if not insp_row:
                raise KeyError(f"Inspection '{inspection_id}' not found in Evidence Ledger.")

            clean_meta = {}
            if insp_row["metadata_json"]:
                try:
                    clean_meta = json.loads(insp_row["metadata_json"])
                except Exception:
                    clean_meta = {}

            inspection_summary = InspectionRecordSummary(
                inspection_id=insp_row["inspection_id"],
                created_at=insp_row["created_at"],
                overall_disposition=ComplianceVerdict(insp_row["overall_disposition"]),
                package_id=insp_row["package_id"],
                summary=insp_row["summary"],
                metadata=clean_meta,
            )

            # 2. Fetch evidence
            ev_rows = conn.execute(
                "SELECT * FROM evidence WHERE inspection_id = ? ORDER BY created_at ASC;",
                (inspection_id,),
            ).fetchall()
            evidence_records: List[EvidenceRecord] = []
            for r in ev_rows:
                qa_obj = None
                if r["quality_assessment_json"]:
                    try:
                        qa_obj = QualityAssessment.model_validate_json(r["quality_assessment_json"])
                    except Exception:
                        qa_obj = None
                evidence_records.append(
                    EvidenceRecord(
                        evidence_id=r["evidence_id"],
                        inspection_id=r["inspection_id"],
                        filename=r["filename"],
                        media_type=r["media_type"],
                        file_size_bytes=r["file_size_bytes"],
                        image_width=r["image_width"],
                        image_height=r["image_height"],
                        quality_assessment=qa_obj,
                        created_at=r["created_at"],
                    )
                )

            # 3. Fetch observations
            obs_rows = conn.execute(
                "SELECT * FROM observations WHERE inspection_id = ? ORDER BY created_at ASC;",
                (inspection_id,),
            ).fetchall()
            observation_records: List[ObservationRecord] = []
            for r in obs_rows:
                sr_obj = None
                if r["source_region_json"]:
                    try:
                        sr_obj = SourceRegion.model_validate_json(r["source_region_json"])
                    except Exception:
                        sr_obj = None
                observation_records.append(
                    ObservationRecord(
                        observation_id=r["observation_id"],
                        inspection_id=r["inspection_id"],
                        field_name=r["field_name"],
                        value=r["value"],
                        confidence=r["confidence"],
                        status=r["status"],
                        source_region=sr_obj,
                        source_type=r["source_type"],
                        parent_observation_id=r["parent_observation_id"],
                        created_at=r["created_at"],
                    )
                )

            # 4. Fetch rule evaluations
            eval_rows = conn.execute(
                "SELECT * FROM rule_evaluations WHERE inspection_id = ? ORDER BY created_at ASC;",
                (inspection_id,),
            ).fetchall()
            rule_eval_records: List[RuleEvaluationRecord] = []
            for r in eval_rows:
                sr_obj = None
                if r["source_region_json"]:
                    try:
                        sr_obj = SourceRegion.model_validate_json(r["source_region_json"])
                    except Exception:
                        sr_obj = None
                rule_eval_records.append(
                    RuleEvaluationRecord(
                        evaluation_id=r["evaluation_id"],
                        inspection_id=r["inspection_id"],
                        rule_id=r["rule_id"],
                        rule_version=r["rule_version"],
                        rule_name=r["rule_name"],
                        statutory_reference=r["statutory_reference"],
                        status=ComplianceVerdict(r["status"]),
                        observed_value=r["observed_value"],
                        expected_requirement=r["expected_requirement"],
                        explanation=r["explanation"],
                        source_region=sr_obj,
                        evidence_reference=r["evidence_reference"],
                        evaluation_stage=r["evaluation_stage"],
                        created_at=r["created_at"],
                    )
                )

            # 5. Fetch review actions
            rev_rows = conn.execute(
                "SELECT * FROM review_actions WHERE inspection_id = ? ORDER BY created_at ASC;",
                (inspection_id,),
            ).fetchall()
            review_action_records: List[ReviewActionRecord] = []
            for r in rev_rows:
                sr_b = None
                if r["source_region_before_json"]:
                    try:
                        sr_b = SourceRegion.model_validate_json(r["source_region_before_json"])
                    except Exception:
                        sr_b = None
                sr_a = None
                if r["source_region_after_json"]:
                    try:
                        sr_a = SourceRegion.model_validate_json(r["source_region_after_json"])
                    except Exception:
                        sr_a = None
                review_action_records.append(
                    ReviewActionRecord(
                        review_id=r["review_id"],
                        inspection_id=r["inspection_id"],
                        field_name=r["field_name"],
                        action=ReviewAction(r["action"]),
                        original_value=r["original_value"],
                        reviewed_value=r["reviewed_value"],
                        original_confidence=r["original_confidence"],
                        source_region_before=sr_b,
                        source_region_after=sr_a,
                        reviewer_notes=r["reviewer_notes"],
                        created_at=r["created_at"],
                    )
                )

        # Reconstruct narrative decision trail
        decision_trail = self._build_decision_trail_summary(
            inspection_summary,
            evidence_records,
            observation_records,
            rule_eval_records,
            review_action_records,
        )

        return FullInspectionTrailResponse(
            inspection=inspection_summary,
            evidence=evidence_records,
            observations=observation_records,
            rule_evaluations=rule_eval_records,
            review_actions=review_action_records,
            decision_trail_summary=decision_trail,
        )

    def list_inspections(self, limit: int = 50, offset: int = 0) -> List[InspectionRecordSummary]:
        """List summary records of inspections in reverse chronological order."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM inspections
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (limit, offset),
            ).fetchall()

            summaries: List[InspectionRecordSummary] = []
            for r in rows:
                meta = {}
                if r["metadata_json"]:
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        meta = {}
                summaries.append(
                    InspectionRecordSummary(
                        inspection_id=r["inspection_id"],
                        created_at=r["created_at"],
                        overall_disposition=ComplianceVerdict(r["overall_disposition"]),
                        package_id=r["package_id"],
                        summary=r["summary"],
                        metadata=meta,
                    )
                )
            return summaries

    def _build_decision_trail_summary(
        self,
        inspection: InspectionRecordSummary,
        evidence: List[EvidenceRecord],
        observations: List[ObservationRecord],
        rule_evaluations: List[RuleEvaluationRecord],
        review_actions: List[ReviewActionRecord],
    ) -> str:
        """Construct a narrative audit trail explaining what evidence and decision path produced the result."""
        lines: List[str] = []
        lines.append(f"Inspection ID: {inspection.inspection_id}")
        lines.append(f"Created At: {inspection.created_at}")
        lines.append(f"Final Disposition: {inspection.overall_disposition.value}")

        if evidence:
            ev = evidence[0]
            lines.append(f"Image Evidence: '{ev.filename}' ({ev.media_type})")
            if ev.quality_assessment:
                lines.append(
                    f"Quality Gate: Score={ev.quality_assessment.overall_score:.2f}, Acceptable={ev.quality_assessment.is_acceptable}"
                )

        ai_obs = [o for o in observations if o.source_type == "ai_extraction"]
        lines.append(f"Observations Recorded: {len(ai_obs)} declarations extracted via AI.")

        initial_evals = [e for e in rule_evaluations if e.evaluation_stage == "initial"]
        lines.append(f"Initial Statutory Evaluations: {len(initial_evals)} checks executed.")

        if review_actions:
            lines.append(f"Human Review: {len(review_actions)} resolution(s) applied:")
            for ra in review_actions:
                lines.append(
                    f" - {ra.field_name}: Action '{ra.action.value}', original='{ra.original_value}', reviewed='{ra.reviewed_value}'. Notes: {ra.reviewer_notes or 'None'}"
                )
            post_evals = [e for e in rule_evaluations if e.evaluation_stage == "post_review"]
            lines.append(
                f"Post-Review Re-evaluation: {len(post_evals)} checks updated disposition to {inspection.overall_disposition.value}."
            )
        else:
            lines.append("Human Review: No human review actions recorded.")

        return "\n".join(lines)
