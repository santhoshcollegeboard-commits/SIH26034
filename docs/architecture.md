# Architecture & System Design — PackCheck (SIH26034)

## 1. System Vision

PackCheck is an evidence-driven compliance verification system tailored for the **Legal Metrology (Packaged Commodities) Rules, 2011** and related statutory frameworks. Physical commodity packages undergo multi-angle visual capture to verify mandatory declarations:
- Manufacturer / Packer / Importer details
- Net quantity declaration & font size compliance
- Month and year of manufacture / packaging / import
- Maximum Retail Price (MRP) declaration (inclusive of all taxes)
- Consumer care details
- Country of origin (for imported goods)
- Best before / expiry date where applicable

## 2. Core Architecture Principle

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ CAPTURE │ ──> │ EXTRACT │ ──> │  CHECK  │ ──> │ REVIEW  │ ──> │ RESULT  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
```

1. **CAPTURE (Input Validation)**:
   - Ingests high-resolution multi-view images of the package.
   - Evaluates image quality (focus, glare, resolution, text readability) before pipeline progression via `ImageQualityChecker`.

2. **EXTRACT (AI / OCR Proposer)**:
   - Identifies candidate text regions, bounding boxes, key-value pairs, and labels.
   - **Crucial Rule**: The AI/OCR module is strictly a *proposer*. It does not decide whether a package is legally compliant.

3. **CHECK (Deterministic Rule Engine)**:
   - Validates extracted declarations against deterministic statutory criteria (e.g., minimum numeral height relative to principal display panel area, mandatory wording, currency formatting).
   - Produces binary or graded rule verdicts (`PASS`, `FAIL`, `UNCERTAIN`).

4. **REVIEW (Human in the Loop)**:
   - Reviewer interface presents extracted bounding boxes, original imagery side-by-side with rule findings.
   - Resolves uncertainty, verifies false positives/negatives, and provides an auditable human sign-off.

5. **RESULT (Evidence Generation)**:
   - Produces tamper-evident compliance audit reports via `EvidenceRepository` and `ReportGenerator`.

## 3. Provider-Independent AI/OCR Architecture

To facilitate fast iteration in Phase 1 (cloud APIs) and offline deployment in Phase 2 (local RTX 4050 6GB), AI services follow a unified provider contract:

```
                  ┌───────────────────────┐
                  │      OCRProvider      │  (Abstract Interface)
                  └───────────────────────┘
                              ▲
               ┌──────────────┴──────────────┐
               │                             │
    ┌───────────────────────┐   ┌───────────────────────┐
    │   CloudOCRProvider    │   │   LocalOCRProvider    │
    │  (Gemini / Groq APIs) │   │  (RTX 4050 Inference) │
    └───────────────────────┘   └───────────────────────┘
```

The application's core logic depends entirely on `OCRProvider`. Neither API keys nor provider-specific payload models leak into downstream services.

## 4. Key Interface Contracts

- **`OCRProvider`**: Handles text and bounding box extraction.
- **`ImageQualityChecker`**: Assesses sharpness, blur, and lighting conditions.
- **`RuleEngine`**: Evaluates compliance using deterministic Legal Metrology rules.
- **`EvidenceRepository`**: Stores packaged audit trails, bounding-box crops, and metadata.
- **`ReportGenerator`**: Produces official audit summaries and exportable compliance certificates.
