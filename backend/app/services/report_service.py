"""PDF Report Service using ReportLab for PackCheck (Step 10).

Generates professional, presentation-ready Legal Metrology compliance inspection reports
strictly from persisted Evidence Ledger records.

Presentation-only safety guarantees:
- Never calls external AI / Gemini.
- Never invokes OCR.
- Never recalculates or overrides rule decisions.
- Never alters ledger state.
- Strictly enforces centralized missing-data policy via formatters.py.
"""

from io import BytesIO
import logging
from typing import Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.result import InspectionResultReport
from backend.app.services.formatters import (
    EMPTY_EVIDENCE_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    EMPTY_REVIEW_ACTIONS_MESSAGE,
    EMPTY_RULE_EVALUATIONS_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    NOT_RECORDED_MESSAGE,
    format_confidence,
    format_missing_value,
    format_source_region,
)

logger = logging.getLogger(__name__)

# Canonical disposition color styling
DISPOSITION_COLORS = {
    ComplianceVerdict.PASS: {
        "text": colors.HexColor("#1b5e20"),
        "bg": colors.HexColor("#e8f5e9"),
        "border": colors.HexColor("#2e7d32"),
    },
    ComplianceVerdict.FAIL: {
        "text": colors.HexColor("#b71c1c"),
        "bg": colors.HexColor("#ffebee"),
        "border": colors.HexColor("#c62828"),
    },
    ComplianceVerdict.REVIEW_REQUIRED: {
        "text": colors.HexColor("#e65100"),
        "bg": colors.HexColor("#fff3e0"),
        "border": colors.HexColor("#ef6c00"),
    },
    ComplianceVerdict.NOT_ASSESSABLE: {
        "text": colors.HexColor("#37474f"),
        "bg": colors.HexColor("#eceff1"),
        "border": colors.HexColor("#546e7a"),
    },
}


class PDFReportService:
    """Service that compiles an InspectionResultReport into a binary PDF document."""

    def generate_report_pdf(self, report: InspectionResultReport) -> bytes:
        """Render the complete inspection report to PDF bytes."""
        buffer = BytesIO()

        # Target printable margins: 36pt (0.5 in), uncompressed text stream for verifiable PDF inspection
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            pageCompression=0,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        style_title = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0d47a1"),
        )
        style_subtitle = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#546e7a"),
        )
        style_section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1a237e"),
            spaceBefore=12,
            spaceAfter=6,
        )
        style_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#263238"),
        )
        style_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=style_cell,
            fontName="Helvetica-Bold",
        )
        style_cell_header = ParagraphStyle(
            "TableCellHeader",
            parent=style_cell,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )
        style_banner = ParagraphStyle(
            "BannerText",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Center
        )
        style_banner_sub = ParagraphStyle(
            "BannerSubText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=1,  # Center
            textColor=colors.HexColor("#37474f"),
        )

        story: List[Any] = []

        # ==================== HEADER ====================
        story.append(Paragraph("PackCheck — Legal Metrology Inspection Platform", style_title))
        story.append(
            Paragraph(
                "Official Statutory Compliance Verification Report &middot; Standards of Weights &amp; Measures (Enforcement) Act",
                style_subtitle,
            )
        )
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0d47a1"), spaceAfter=10))

        # Header Info Table
        pkg_id = format_missing_value(report.package_id)
        created_at_str = format_missing_value(report.created_at)
        statutory_regime = format_missing_value(report.traceability.statutory_source)

        header_data = [
            [
                Paragraph(f"<b>Inspection ID:</b> {report.inspection_id}", style_cell),
                Paragraph(f"<b>Date &amp; Time (UTC):</b> {created_at_str}", style_cell),
            ],
            [
                Paragraph(f"<b>Package Reference:</b> {pkg_id}", style_cell),
                Paragraph(f"<b>Statutory Regime:</b> {statutory_regime}", style_cell),
            ],
        ]
        header_table = Table(header_data, colWidths=[270, 270])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fa")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 10))

        # ==================== VERDICT BANNER ====================
        disposition = report.overall_disposition
        color_theme = DISPOSITION_COLORS.get(
            disposition,
            {
                "text": colors.black,
                "bg": colors.HexColor("#eeeeee"),
                "border": colors.gray,
            },
        )
        banner_style = ParagraphStyle(
            "VerdictStyle",
            parent=style_banner,
            textColor=color_theme["text"],
        )

        explanation = format_missing_value(
            report.summary,
            fallback=f"Statutory verdict determined deterministically as {disposition.value}.",
        )

        banner_data = [
            [Paragraph(f"FINAL STATUTORY DISPOSITION: {disposition.value}", banner_style)],
            [Paragraph(explanation, style_banner_sub)],
        ]
        banner_table = Table(banner_data, colWidths=[540])
        banner_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color_theme["bg"]),
                    ("BOX", (0, 0), (-1, -1), 1.5, color_theme["border"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        )
        story.append(banner_table)
        story.append(Spacer(1, 12))

        # ==================== SECTION 1: EVIDENCE & QUALITY ====================
        story.append(Paragraph("1. Image Evidence &amp; Capture Quality", style_section_heading))
        ev = report.evidence
        if ev:
            dims = (
                f"{ev.image_width} x {ev.image_height} px"
                if ev.image_width and ev.image_height
                else NOT_AVAILABLE_MESSAGE
            )
            size = (
                f"{ev.file_size_bytes:,} bytes"
                if ev.file_size_bytes
                else NOT_AVAILABLE_MESSAGE
            )
            q_status = (
                "PASS (Acceptable for inspection)"
                if ev.quality_assessment and ev.quality_assessment.is_acceptable
                else "REJECTED (Insufficient quality)"
                if ev.quality_assessment
                else NOT_AVAILABLE_MESSAGE
            )
            q_score = (
                f"{ev.quality_assessment.overall_score:.2f} / 1.00"
                if ev.quality_assessment
                else NOT_AVAILABLE_MESSAGE
            )

            ev_rows = [
                [
                    Paragraph("<b>Filename / Safe ID:</b>", style_cell_bold),
                    Paragraph(format_missing_value(ev.filename), style_cell),
                    Paragraph("<b>Media MIME Type:</b>", style_cell_bold),
                    Paragraph(format_missing_value(ev.media_type), style_cell),
                ],
                [
                    Paragraph("<b>Evidence ID:</b>", style_cell_bold),
                    Paragraph(format_missing_value(ev.evidence_id), style_cell),
                    Paragraph("<b>Dimensions &amp; Size:</b>", style_cell_bold),
                    Paragraph(f"{dims} ({size})", style_cell),
                ],
                [
                    Paragraph("<b>Quality Gate Verdict:</b>", style_cell_bold),
                    Paragraph(q_status, style_cell),
                    Paragraph("<b>Quality Gate Score:</b>", style_cell_bold),
                    Paragraph(q_score, style_cell),
                ],
            ]
            ev_table = Table(ev_rows, colWidths=[120, 150, 120, 150])
            ev_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0bec5")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#eceff1")),
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
                        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8f9fa")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(ev_table)
        else:
            # Rule 8: Meaningful section-level message for empty evidence collection (no empty table)
            no_ev_p = Paragraph(f"<i>{EMPTY_EVIDENCE_MESSAGE}</i>", style_cell)
            no_ev_table = Table([[no_ev_p]], colWidths=[540])
            no_ev_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(no_ev_table)

        story.append(Spacer(1, 10))

        # ==================== SECTION 2: EXTRACTED DECLARATIONS ====================
        story.append(Paragraph("2. Mandatory Packaging Declarations", style_section_heading))
        if report.observations:
            decl_headers = [
                Paragraph("Field Name", style_cell_header),
                Paragraph("Observed Value", style_cell_header),
                Paragraph("Confidence", style_cell_header),
                Paragraph("Status", style_cell_header),
                Paragraph("Provenance / Source", style_cell_header),
                Paragraph("Source Bounding Box", style_cell_header),
            ]
            decl_rows = [decl_headers]

            for obs in report.observations:
                val_str = format_missing_value(obs.value)
                conf_str = format_confidence(obs.confidence)
                sr_str = format_source_region(obs.source_region)
                status_str = format_missing_value(obs.status, fallback=NOT_RECORDED_MESSAGE)

                source_type_str = str(obs.source_type)
                if "correct" in source_type_str:
                    source_badge = "Reviewer Correction"
                elif "confirm" in source_type_str:
                    source_badge = "Reviewer Confirmed"
                elif "unrecorded" in source_type_str:
                    source_badge = "Not Recorded"
                else:
                    source_badge = "AI Extracted"

                f_name = obs.field_name.replace("_", " ").title()

                decl_rows.append(
                    [
                        Paragraph(f"<b>{f_name}</b>", style_cell),
                        Paragraph(val_str, style_cell),
                        Paragraph(conf_str, style_cell),
                        Paragraph(status_str, style_cell),
                        Paragraph(source_badge, style_cell),
                        Paragraph(sr_str, style_cell),
                    ]
                )

            decl_table = Table(decl_rows, colWidths=[95, 155, 55, 60, 95, 80])
            decl_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#283593")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0bec5")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ]
                )
            )
            story.append(decl_table)
        else:
            # Rule 8: Meaningful section-level message for empty observations (no empty table)
            no_obs_p = Paragraph(f"<i>{EMPTY_OBSERVATIONS_MESSAGE}</i>", style_cell)
            no_obs_table = Table([[no_obs_p]], colWidths=[540])
            no_obs_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(no_obs_table)

        story.append(Spacer(1, 10))

        # ==================== SECTION 3: RULE EVALUATIONS ====================
        story.append(Paragraph("3. Deterministic Statutory Rule Evaluations", style_section_heading))
        if report.rule_evaluations:
            rule_headers = [
                Paragraph("Rule ID / Version", style_cell_header),
                Paragraph("Statutory Reference", style_cell_header),
                Paragraph("Status", style_cell_header),
                Paragraph("Observed Value", style_cell_header),
                Paragraph("Legal Requirement &amp; Deterministic Explanation", style_cell_header),
                Paragraph("Stage", style_cell_header),
            ]
            rule_rows = [rule_headers]

            for r in report.rule_evaluations:
                # Rule 6 & 10: Persisted status is canonical and unchanged
                status_color = DISPOSITION_COLORS.get(r.status, {}).get("text", colors.black)
                status_p = Paragraph(
                    f"<b>{r.status.value}</b>",
                    ParagraphStyle("StatusP", parent=style_cell, textColor=status_color),
                )
                exp_req_val = format_missing_value(r.expected_requirement)
                explanation_val = format_missing_value(r.explanation)
                obs_val = format_missing_value(r.observed_value)
                stat_ref_val = format_missing_value(r.statutory_reference)

                req_exp = (
                    f"<b>Requirement:</b> {exp_req_val}<br/>"
                    f"<b>Explanation:</b> {explanation_val}"
                )
                rule_rows.append(
                    [
                        Paragraph(f"<b>{r.rule_id}</b><br/><font color='#546e7a'>{r.rule_version}</font>", style_cell),
                        Paragraph(stat_ref_val, style_cell),
                        status_p,
                        Paragraph(obs_val, style_cell),
                        Paragraph(req_exp, style_cell),
                        Paragraph(format_missing_value(r.evaluation_stage), style_cell),
                    ]
                )

            rule_table = Table(rule_rows, colWidths=[130, 90, 55, 75, 140, 50])
            rule_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0bec5")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ]
                )
            )
            story.append(rule_table)
        else:
            # Rule 8: Meaningful section-level message for empty rule evaluations (no empty table)
            no_rules_p = Paragraph(f"<i>{EMPTY_RULE_EVALUATIONS_MESSAGE}</i>", style_cell)
            no_rules_table = Table([[no_rules_p]], colWidths=[540])
            no_rules_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(no_rules_table)

        story.append(Spacer(1, 10))

        # ==================== SECTION 4: HUMAN REVIEW AUDIT LOG ====================
        story.append(Paragraph("4. Human Review Audit Log", style_section_heading))
        if report.review_actions:
            rev_headers = [
                Paragraph("Field", style_cell_header),
                Paragraph("Action", style_cell_header),
                Paragraph("Original AI Value", style_cell_header),
                Paragraph("Reviewed / Corrected Value", style_cell_header),
                Paragraph("Inspector Notes", style_cell_header),
                Paragraph("Timestamp", style_cell_header),
            ]
            rev_rows = [rev_headers]
            for ra in report.review_actions:
                action_name = ra.action.upper() if isinstance(ra.action, str) else ra.action.value.upper()
                rev_rows.append(
                    [
                        Paragraph(f"<b>{ra.field_name.replace('_', ' ').title()}</b>", style_cell),
                        Paragraph(action_name, style_cell),
                        Paragraph(format_missing_value(ra.original_value), style_cell),
                        Paragraph(format_missing_value(ra.reviewed_value), style_cell),
                        Paragraph(format_missing_value(ra.reviewer_notes, fallback="No notes recorded."), style_cell),
                        Paragraph(format_missing_value(ra.created_at), style_cell),
                    ]
                )
            rev_table = Table(rev_rows, colWidths=[90, 60, 95, 105, 110, 80])
            rev_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e65100")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0bec5")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff8e1")]),
                    ]
                )
            )
            story.append(rev_table)
        else:
            # Rule 7 & 8: Explicitly record empty review action list (no empty table)
            no_rev_p = Paragraph(f"<i>{EMPTY_REVIEW_ACTIONS_MESSAGE}</i>", style_cell)
            no_rev_table = Table([[no_rev_p]], colWidths=[540])
            no_rev_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfd8dc")),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(no_rev_table)

        story.append(Spacer(1, 10))

        # ==================== SECTION 5: TRACEABILITY & DECISION TRAIL ====================
        trail_flowables: List[Any] = [
            Paragraph("5. Audit Traceability &amp; Decision Trail", style_section_heading),
            Paragraph(
                f"<b>Decision Chain:</b> {format_missing_value(report.traceability.provenance_chain)}<br/>"
                f"<b>Rule Engine:</b> {format_missing_value(report.traceability.rule_engine_version)} &middot; "
                f"<b>Evaluations Executed:</b> {report.traceability.evaluated_rule_count} total "
                f"({report.traceability.initial_rule_count} initial, {report.traceability.post_review_rule_count} post-review)",
                style_cell,
            ),
            Spacer(1, 4),
        ]
        decision_trail_str = format_missing_value(report.decision_trail_summary)
        trail_lines = decision_trail_str.replace("\n", "<br/>")
        trail_flowables.append(
            Table(
                [[Paragraph(f"<font color='#37474f'>{trail_lines}</font>", style_cell)]],
                colWidths=[540],
                style=[
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#90a4ae")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eceff1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ],
            )
        )
        story.append(KeepTogether(trail_flowables))
        story.append(Spacer(1, 12))

        # ==================== FOOTER ====================
        footer_text = (
            "This document is an official statutory audit report generated deterministically by PackCheck. "
            "Evidence records and decision paths are permanently preserved in the Evidence Ledger pursuant to "
            "the Legal Metrology Act, 2009 and Packaged Commodities Rules, 2011."
        )
        story.append(
            KeepTogether(
                [
                    HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#b0bec5"), spaceAfter=6),
                    Paragraph(
                        f"<font color='#78909c' size='7'>{footer_text}</font>",
                        style_subtitle,
                    ),
                ]
            )
        )

        # Build document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
