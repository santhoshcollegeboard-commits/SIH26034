# Legal Metrology Deterministic Rules Library

This directory documents the statutory rule specifications implemented in PackCheck under the **Legal Metrology (Packaged Commodities) Rules, 2011** (as amended by the Ministry of Consumer Affairs, Food and Public Distribution, Government of India).

## Core Architecture Principle

```
AI / OCR EXTRACTS  ──>  DETERMINISTIC RULES DECIDE  ──>  HUMANS RESOLVE UNCERTAINTY
```

- AI/OCR models (Gemini Vision) are strictly *proposers* of text and bounding boxes.
- Statutory compliance decisions (`PASS`, `FAIL`, `NOT_VERIFIABLE`, `NOT_APPLICABLE`) are computed by deterministic Python evaluators in [`backend/app/services/rules/`](../backend/app/services/rules/).
- Missing or unreadable text on a single image is marked `NOT_VERIFIABLE` / `FLAGGED_FOR_REVIEW`, never assumed to be a criminal defect without inspector verification.

---

## Implemented Statutory Rule Specifications

| Rule ID | Statutory Reference | Rule Title | Expected Condition | Evaluator |
| :--- | :--- | :--- | :--- | :--- |
| `LM-PC-06-1-A` | Rule 6(1)(a) | Product Name / Generic Identity | Common or generic name must be clearly stated (>= 2 chars) | `evaluate_product_name` |
| `LM-PC-06-1-B` | Rule 6(1)(b) | Manufacturer / Packer / Importer Details | Name and complete address of manufacturer, packer, or importer | `evaluate_manufacturer_details` |
| `LM-PC-06-1-B-ORIGIN` | Rule 6(1)(b) Proviso & Rule 6(10) | Country of Origin (Imported Commodities) | Mandatory country of origin or manufacture for imported goods | `evaluate_country_of_origin` |
| `LM-PC-06-1-C` | Rule 6(1)(c) | Net Quantity Presence | Net quantity declaration must be present on principal display panel | `evaluate_net_quantity_presence` |
| `LM-PC-11-UNITS` | Rules 11, 12, 13 & Second Schedule | Standard Units & Metric Formatting | Approved SI symbols (`g`, `kg`, `ml`, `l`); prohibited abbreviations (`gms`, `kilo`) or bare numbers rejected | `evaluate_standard_metric_units` |
| `LM-PC-06-1-D` | Rule 6(1)(d) | Month & Year of Manufacture / Packing | Mandatory month and year in recognizable date format (`MM/YYYY`, `Month YYYY`) | `evaluate_manufacturing_date` |
| `LM-PC-06-1-E` | Rule 6(1)(e) | Maximum Retail Price & Tax Disclaimer | MRP in Rupees, mandatory 'inclusive of all taxes' or 'incl. of all taxes' | `evaluate_mrp_declaration` |
| `LM-PC-06-1-F` | Rule 6(1)(f) | Consumer Care Grievance Redressal | Name, address, telephone/toll-free or email for consumer complaints | `evaluate_consumer_care` |
| `LM-PC-06-1-H-USP` | Rule 6(1)(h) (2021 Amendment) | Unit Sale Price (USP) | Mandatory unit sale price (per g/100g, kg, ml/100ml, l, or number) for packages exceeding small-package exemption threshold (> 10 g / > 10 ml) | `evaluate_unit_sale_price` |

---

## Verdict Aggregation States

1. **`FAIL`**: Triggered if any applicable statutory rule fails (e.g. prohibited unit `gms`, missing tax disclaimer on MRP, bare number without unit).
2. **`FLAGGED_FOR_REVIEW`**: Triggered if zero rules fail, but one or more mandatory fields are unreadable or undetected on the current package angle.
3. **`PASS`**: Triggered only when all applicable statutory checks pass and zero mandatory declarations are missing or unreadable.
