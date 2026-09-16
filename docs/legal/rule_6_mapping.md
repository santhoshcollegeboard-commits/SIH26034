# Rule 6 Implementation Mapping

This document provides the authoritative mapping between **Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011** and the **PackCheck** compliance engine.

---

## 1. Regulatory Source

* **Official Title**: The Legal Metrology (Packaged Commodities) Rules, 2011
* **Issuing Authority**: Ministry of Consumer Affairs, Food and Public Distribution (Department of Consumer Affairs), Central Government of India
* **Enacting Power**: Sub-section (1) read with clauses (j) and (q) of sub-section (2) of section 52 of the Legal Metrology Act, 2009 (1 of 2010)
* **Gazette Publication**: Extraordinary, Part II — Section 3 — Sub-section (i), Notification No. **G.S.R. 101(E)**
* **Date of Gazette Notification**: New Delhi, the 7th March, 2011
* **Commencement / Effective Date**: 1st day of April, 2011 (Rule 1(2))
* **Document Reference File**: `docs/legal/sources/India Code __ PDF Ebook Viewer.html` (Original Official Gazette text published on India Code repository)

---

## 2. Rule 6 Location

* **Statutory Heading**: Chapter II — Provisions Applicable to Packages Intended for Retail Sale
* **Rule Number & Title**: **Rule 6. Declarations to be made on every package.**
* **Gazette Pagination**: Pages 43 to 46 of the official Gazette publication (G.S.R. 101(E))

---

## 3. Applicable Clauses

Rule 6 consists of five sub-rules:

* **Sub-rule (1)**: Mandates that every package bear a definite, plain, and conspicuous declaration made on the package or securely affixed label regarding:
  * **Clause (a)**: Name and address of the manufacturer, or where the manufacturer is not the packer, the name and address of the manufacturer and packer; for imported packages, the name and address of the importer.
    * *Explanation I*: Presumption of manufacturer if name/address appears without "manufactured by" or "packed by".
    * *Explanation II*: Brand owner / marketer deemed responsible; first manufacturer prosecuted if multiple appear.
    * *Explanation III*: Food articles governed by Prevention of Food Adulteration Act, 1954 (now FSSAI).
  * **Clause (b)**: Common or generic names of the commodity contained in the package; for multi-product packages, name and quantity of each.
  * **Clause (c)**: Net quantity in terms of standard unit of weight or measure, or by number.
  * **Clause (d)**: Month and year of manufacture, pre-packing, or import.
    * *Provisos*: Exemptions/governance for food, seeds, rubber stamps, and cosmetics.
    * *Explanation I*: Month and year expressed in words, numerals, or both.
  * **Clause (e)**: Retail sale price of the package (MRP inclusive of all taxes).
    * *Proviso*: State excise laws for alcoholic beverages.
  * **Clause (f)**: Dimensions of the commodity pieces where sizes are relevant.
  * **Clause (g)**: Other specified matters, with provisos detailing statutory exemptions:
    * *(A)* Month/year exemption for bidi, incense sticks, domestic LPG cylinders (14.2 kg / 5 kg PSU).
    * *(B)* Exhaustion of packaging material in succeeding month.
    * *(C)* Retail sale price exemption for bidi and domestic LPG under Administered Price Mechanism.
* **Sub-rule (2)**: Mandatory consumer care details: Name, address, telephone number, and e-mail address (if available) of the person or office to be contacted for consumer complaints.
* **Sub-rule (3)**: Prohibition on individual stickers for altering or making declarations, provided that a sticker with a revised *lower* MRP (inclusive of all taxes) is permissible if it does not cover the original MRP.
* **Sub-rule (4)**: Permission to use stickers for non-statutory declarations.
* **Sub-rule (5)**: Declarations on multi-component packages and spare parts.

---

## 4. Amendment / Version Information

* **Base Statutory Baseline**: Original 2011 Rules (Notification G.S.R. 101(E), effective 1 April 2011).
* **PackCheck Version Identifier**: `LMR-2011-BASE-R06`
* **Subsequent Statutory Milestones (To Be Versioned Explicitly When Sources Added)**:
  * *2017 Amendments (G.S.R. 629(E))*: Introduction of E-commerce declarations, bar-coding provisions, font size alignments.
  * *2021 Amendments (G.S.R. 779(E))*: Introduction of Unit Sale Price (USP), date of manufacture format standardization, removal of Schedule II pack sizes.

---

## 5. Requirement Mapping

| Rule / Clause | Regulatory Requirement | Existing PackCheck Extraction Field | Can OCR/Image Detect? | Evidence Required | Deterministic Check Possible? | Status: Compliant | Status: Non-Compliant | Status: Insufficient Evidence | Classification | Notes / Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Rule 6(1)(a)** | Manufacturer Name & Address | `manufacturer_name`, `manufacturer_address` | Yes | Label region showing name and physical address | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | High confidence text presence and address pattern verification. |
| **Rule 6(1)(a)** | Packer Name & Address (if different from manufacturer) | `packer_name` | Partial | Label region showing "Packed by" | Partial | `PASS` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | System cannot know whether third-party packing applies without package metadata. |
| **Rule 6(1)(a)** | Importer Name & Address (for imported goods) | `importer_name` | Partial | Label region showing "Imported by" | Partial | `PASS` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | Applicable only if commodity is imported. Missing importer on domestic product is compliant. |
| **Rule 6(1)(b)** | Common or Generic Commodity Name | `product_name` | Yes | Principal display label showing product identity | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | Non-empty text verification matching product title. |
| **Rule 6(1)(c)** | Net Quantity in standard metric units | `net_quantity` | Yes | Weight/volume/number text statement | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | Verifies presence and legal unit regex (`g`, `kg`, `ml`, `l`, `m`, `N`, etc.). Font height evaluated under Rule 7. |
| **Rule 6(1)(d)** | Month and Year of Manufacture / Pre-packing | `month_year_of_manufacture` | Yes | Date statement in words or numerals | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | Regex matching month/year patterns (`MM/YYYY`, `Mon YYYY`, `MM/YY`). Exemptions (bidi, LPG, incense) flagged. |
| **Rule 6(1)(e)** | Retail Sale Price (MRP inclusive of all taxes) | `mrp` | Yes | Price declaration with "MRP" / "₹" / "Rs." | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | Verifies currency symbol/prefix, numeric amount, and "incl. of all taxes" phrasing where visible. |
| **Rule 6(1)(f)** | Dimensions of individual pieces | *None* | No | Dimensions statement (`cm`, `mm`, `m`) | No | N/A | N/A | `NOT_ASSESSABLE` | `NOT_ASSESSABLE_FROM_CURRENT_EVIDENCE` | Relevant only for specific commodity classes (e.g. bedsheets, tiles). Field absent from extraction schema. |
| **Rule 6(2)** | Consumer Care Details (Phone, Email, Address) | `consumer_care_details` | Yes | Consumer care contact statement | Yes | `PASS` | `FAIL` | `REVIEW_REQUIRED` | `MACHINE_CHECKABLE` | Verifies presence of phone number or email regex or physical grievance address. |
| **Rule 6(3)** | Prohibition of individual stickers altering declarations | *None* | Partial | Visual evidence of overlay sticker | No | N/A | `FAIL` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | Physical sticker edge detection / tampering cannot be authoritatively decided by optical OCR alone; triggers reviewer escalation. |
| **Rule 6(5)** | Multi-component package declarations | *None* | No | Accompanying package manifests | No | N/A | N/A | `NOT_ASSESSABLE` | `NOT_ASSESSABLE_FROM_CURRENT_EVIDENCE` | Multi-angle single-pack images cannot observe separate internal or accompanying units. |

---

## 6. Existing Extraction Fields vs. Rule 6 Requirements

The current backend extraction contract ([backend/app/schemas/extraction.py](file:///c:/SIH/SIH26034/backend/app/schemas/extraction.py)) maps directly to 7 of the core Rule 6 declarations:

| Existing Field in `ExtractionResult` | Rule 6 Clause | Confidence Field Available? | Bounding Box (`SourceRegion`) Available? | Status Representation |
| :--- | :--- | :--- | :--- | :--- |
| `product_name` | Rule 6(1)(b) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `manufacturer_name` | Rule 6(1)(a) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `manufacturer_address` | Rule 6(1)(a) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `packer_name` | Rule 6(1)(a) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `importer_name` | Rule 6(1)(a) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `net_quantity` | Rule 6(1)(c) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `mrp` | Rule 6(1)(e) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `month_year_of_manufacture` | Rule 6(1)(d) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |
| `consumer_care_details` | Rule 6(2) | Yes (`0.0–1.0`) | Yes (`x, y, width, height`) | `extracted`, `unreadable`, `not_found` |

### Missing Representations

1. `dimensions` (Rule 6(1)(f)): Not represented in current schemas.
2. `sticker_alteration_flag` (Rule 6(3)): Not represented in current schemas.
3. Structured unit/number breakdown: `net_quantity` is a raw string, preventing immediate numerical threshold computation without secondary parsing.

---

## 7. Machine-Checkable Requirements

These 6 requirements can be deterministically evaluated by the Rule Engine directly from high-confidence extraction observations:

1. **Rule 6(1)(a) — Manufacturer Declaration**:
   * Check: `manufacturer_name.status == 'extracted'` AND non-empty string.
   * Address Check: `manufacturer_address.status == 'extracted'` AND non-empty string.
2. **Rule 6(1)(b) — Generic Name Declaration**:
   * Check: `product_name.status == 'extracted'` AND non-empty string.
3. **Rule 6(1)(c) — Net Quantity Mandatory Unit**:
   * Check: `net_quantity.status == 'extracted'` AND matches metric unit pattern (`g`, `kg`, `ml`, `l`, `m`, `cm`, `N`).
4. **Rule 6(1)(d) — Month & Year Format**:
   * Check: `month_year_of_manufacture.status == 'extracted'` AND matches valid calendar date pattern (word or numeral).
5. **Rule 6(1)(e) — Retail Sale Price (MRP)**:
   * Check: `mrp.status == 'extracted'` AND contains currency indicator and numeric price value.
6. **Rule 6(2) — Consumer Care Facility**:
   * Check: `consumer_care_details.status == 'extracted'` AND contains valid phone digits, `@` email, or physical address.

---

## 8. Review-Required Requirements

These requirements cannot be authoritatively decided solely by automated regex or OCR and must escalate to `REVIEW_REQUIRED`:

1. **Packer / Importer Applicability (Rule 6(1)(a))**:
   * Whether a package is domestically manufactured vs. imported, or whether packing was outsourced, requires commercial context.
2. **Sticker Alteration / Tampering (Rule 6(3))**:
   * Suspected over-stickering, price reduction stickers, or label defacement must be visually confirmed by a human inspector.
3. **Low-Confidence Extractions**:
   * Any declaration where OCR confidence is below the defined reliability threshold ($< 0.70$) or where `status == 'unreadable'` MUST escalate to `REVIEW_REQUIRED`.

---

## 9. Not-Assessable Requirements

These statutory provisions cannot be determined from standard optical packaging photographs:

1. **Piece Dimensions for Variable Commodities (Rule 6(1)(f))**:
   * Physical dimensions of internal pieces when size is relevant cannot be inferred without product classification metadata and multi-angle measurement references.
2. **Multi-Component Accompanying Units (Rule 6(5))**:
   * Units packed in separate accompanying boxes or sold as spare parts cannot be inspected from a single packaging image.
3. **Physical Weight / Measure Verification**:
   * The actual physical mass or volume inside the package (gravimetric verification) cannot be verified optically.

---

## 10. Evidence Requirements

To substantiate each Rule 6 check, the evidence repository must preserve:

1. **Original Unprocessed Image**: Base evidence with SHA-256 hash.
2. **Cropped Image Region**: Pixel crop corresponding to `source_region` bounding box for the specific declaration.
3. **Observation Record**: Extracted text, model confidence, and provider identifier.
4. **Statutory Reference**: Citation of `LMR-2011-BASE-R06` and specific clause (e.g. `Clause (e)` for MRP).

---

## 11. Implementation Notes

* The deterministic engine must operate strictly as:
  $$\text{ExtractedField} \longrightarrow \text{Statutory Validator} \longrightarrow \text{RuleEvaluation}$$
* Under no circumstances should the AI model decide whether a declaration complies with Rule 6.
* If an essential field is marked `not_found`, the rule verdict is `FAIL` (statutory violation for missing mandatory declaration).
* If an essential field is marked `unreadable`, the rule verdict is `REVIEW_REQUIRED` (system does not guess or assume non-compliance).

---

## 12. Traceability

* **Primary Statutory Document**: The Legal Metrology (Packaged Commodities) Rules, 2011 (Notification G.S.R. 101(E)).
* **Local Source Copy**: `docs/legal/sources/India Code __ PDF Ebook Viewer.html`
* **Rule Engine Target**: `backend/app/services/rule_engine_service.py`
* **Target Rule Module**: `rules/rule_6_declarations.py`
* **Schema Contract**: [backend/app/schemas/compliance.py](file:///c:/SIH/SIH26034/backend/app/schemas/compliance.py) (`RuleEvaluation`, `ComplianceVerdict`, `InspectionResult`).

---

## Implementation Boundary

PackCheck **WILL** automatically determine:

* Presence or absence of mandatory Rule 6 declarations (Manufacturer, Product Name, Net Quantity, MRP, Mfg Date, Consumer Care).
* Conformance of Net Quantity declarations to standard metric unit abbreviations.
* Conformance of Month & Year declarations to recognized temporal formats.
* Conformance of MRP declarations to price and currency notation.
* Escalation to human review when image quality or OCR confidence is borderline.

PackCheck **WILL NOT** attempt to automatically determine:

* Whether an absent importer address is legal without knowing if the good is imported.
* Whether internal components of a multi-piece set match external declarations.
* The physical accuracy of weight/volume inside the package.
* Statutory exemptions under special laws (e.g., Seeds Act, State Excise) without external product categorization.
