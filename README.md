---

## Core Functional Modules

PackCheck is organized into focused modules so that image processing, data extraction, statutory validation, and reporting can evolve independently.

### 1. Image Capture and Input Validation

The capture stage receives package images and prepares them for downstream processing.

Responsibilities include:

- Accepting supported image formats.
- Checking whether an uploaded file is readable.
- Identifying missing or invalid image data.
- Checking image dimensions and basic quality indicators.
- Detecting images that may be unsuitable for reliable extraction.
- Preserving the original uploaded image for reference where supported.
- Returning clear validation messages when processing cannot continue.

The capture stage should reject invalid inputs before invoking an external AI provider. This reduces unnecessary processing and makes failures easier to diagnose.

### 2. OCR and Information Extraction

The extraction stage identifies potentially relevant information printed on a package.

Typical extraction targets include:

- Commodity or product name.
- Manufacturer, packer, or importer information.
- Net quantity or declared quantity.
- Maximum Retail Price (MRP).
- Manufacturing or packing date.
- Consumer-care information.
- Unit sale price, where applicable.
- Country of origin, where applicable.
- Other declarations relevant to the selected compliance rules.

Extracted information must remain distinguishable from verified statutory facts. A readable declaration is not automatically a legally compliant declaration.

### 3. Deterministic Compliance Engine

The rules engine evaluates extracted information against explicitly defined validation conditions.

Its responsibilities include:

- Checking required field presence.
- Validating extracted values against expected formats.
- Applying field-specific validation logic.
- Evaluating applicable statutory requirements.
- Identifying missing, invalid, or inconsistent declarations.
- Producing structured findings for further review.
- Keeping extraction logic separate from compliance decisions.

Rule outcomes should be explainable and reproducible for the same inputs and rule configuration.

### 4. Human Review and Resolution

Human review is necessary when the available evidence does not support a reliable automated conclusion.

Review may be appropriate when:

- The image is blurred or partially obscured.
- OCR produces conflicting candidate values.
- A declaration is visible but difficult to interpret.
- A field is not applicable to a particular commodity.
- A rule requires contextual interpretation.
- An extracted value appears inconsistent with another declaration.
- The applicable legal requirement needs confirmation.

A reviewer should be able to distinguish an extraction error from a genuine compliance concern.

### 5. Results and Evidence Reporting

The result stage presents the outcome of the processing pipeline.

A useful result should communicate:

- Which declarations were extracted.
- Which validations were performed.
- Which requirements passed or failed.
- Which fields remain uncertain.
- What evidence supports each finding.
- Which items require human attention.
- Which rule definitions were used for evaluation.

The report should avoid presenting uncertain extraction results as established legal violations.

---

## Legal Metrology Compliance Scope

PackCheck focuses on helping users inspect physical packaged commodities against applicable Legal Metrology requirements in India.

The exact requirements depend on the commodity, package type, applicable exemptions, current rules, and relevant amendments.

### Regulatory Reference

The principal regulatory reference for the project is the Legal Metrology (Packaged Commodities) Rules, 2011, together with applicable amendments and related provisions.

Official sources should be consulted before implementing or updating statutory rules:

- Department of Consumer Affairs: https://consumeraffairs.nic.in/
- India Code: https://www.indiacode.nic.in/
- Legal Metrology resources published by the relevant government authorities.

The project should maintain a clear distinction between the text of a legal provision, its software representation, and the outcome of an individual package inspection.

### Declaration Categories

Depending on applicability, the compliance engine may evaluate declarations relating to the following categories.

#### Product Identification

- Name or identity of the commodity.
- Description needed to identify the packaged product.
- Consistency between the product description and other extracted declarations.

#### Manufacturer, Packer, and Importer Details

- Name of the relevant business entity.
- Address declarations.
- Identification of the responsible entity.
- Importer-related declarations, where applicable.

#### Quantity Declarations

- Declared net quantity.
- Measurement unit.
- Quantity format and numerical consistency.
- Distinction between net quantity and gross package weight.
- Applicability of quantity-related requirements.

#### Price Declarations

- Maximum Retail Price.
- Currency representation.
- Price formatting and numerical parsing.
- Detection of missing or ambiguous price information.
- Distinction between printed price and other monetary values.

#### Date and Traceability Information

- Manufacturing date, where applicable.
- Packing date, where applicable.
- Other relevant date declarations.
- Preservation of the original date text.
- Detection of ambiguous or incomplete date formats.

#### Consumer Information

- Consumer-care details, where applicable.
- Contact information and address declarations.
- Readability of relevant printed information.
- Presence of the information required by the applicable rule.

These categories represent potential validation targets, not a claim that every field is mandatory for every packaged commodity.

---

## Compliance Result Semantics

PackCheck should use explicit result categories so that users can understand the difference between a successful validation and an unresolved inspection.

### Pass

A pass indicates that the evaluated condition was satisfied using the available evidence and the configured rule.

It does not imply that every possible legal requirement for the package has been checked.

### Fail

A fail indicates that the evaluated condition was not satisfied according to the applicable rule and the evidence used by the engine.

The associated finding should identify the relevant field, expected condition, observed value, and rule reference whenever available.

### Needs Review

Needs Review indicates that the system cannot responsibly produce a definitive automated conclusion.

Examples include uncertain OCR output, conflicting values, insufficient image quality, and rules requiring additional context.

### Not Evaluated

Not Evaluated indicates that a validation was not performed.

Possible reasons include:

- A required input was unavailable.
- The rule was not configured.
- The field was outside the current evaluation scope.
- A prerequisite validation could not be completed.

### Not Applicable

Not Applicable should be used only when the applicability conditions of a rule establish that the requirement does not apply.

A missing declaration must not automatically be classified as Not Applicable.

### Error

An error indicates a technical or processing failure rather than a legal compliance result.

Examples include provider failures, malformed responses, unexpected internal exceptions, and unsuccessful processing of an uploaded image.

Technical errors must not be silently converted into compliance passes.

---

## Extraction Data and Evidence Model

Structured extraction allows downstream services to consume model output without depending on provider-specific response formats.

### Extracted Field Representation

An extracted field can conceptually contain the following information:

- Field identifier.
- Original extracted text.
- Normalized value, when normalization is appropriate.
- Extraction confidence, when supplied or meaningfully calculated.
- Bounding-box coordinates, when available.
- Source image reference.
- Validation status.
- Associated warnings.
- Supporting evidence metadata.

The exact fields should follow the application's existing Pydantic schemas.

### Original Text and Normalized Values

PackCheck should preserve the original extracted text whenever possible.

For example, an image may contain a quantity declaration written as `500 g`.

The application may normalize this value into a structured representation containing a numerical quantity and unit.

Both representations serve different purposes:

- Original text preserves what was printed.
- Normalized data supports deterministic validation.
- Evidence links help reviewers verify the interpretation.

Normalization must not silently change the meaning of a declaration.

### Bounding Boxes and Visual Evidence

When the OCR provider supplies bounding boxes, they can help connect extracted declarations to their locations on the package.

Bounding-box metadata may support:

- Locating the declaration on the original image.
- Reviewing extraction mistakes.
- Comparing multiple declarations.
- Investigating conflicting values.
- Connecting a reported finding to visible package evidence.

Coordinates should be interpreted using a documented convention, such as image-relative pixel coordinates or normalized coordinates.

If bounding boxes are unavailable, the system should not fabricate them.

### Confidence and Uncertainty

Extraction confidence describes the certainty associated with an extraction result, subject to the provider's confidence definition.

It is not equivalent to the probability that a package complies with the law.

A high-confidence extraction can still contain an incorrect value. Similarly, a correctly extracted declaration may fail a statutory validation.

The system should keep these concepts separate:

1. Extraction confidence.
2. Validation outcome.
3. Overall inspection completeness.
4. Human-review status.

---

## Deterministic Rules Engine Design

The rules engine is the central compliance decision component.

It should consume structured inputs and applicable rule definitions rather than relying on a generative model to decide whether a package is legally compliant.

### Rule Definition Principles

Each rule should ideally identify:

- A unique rule identifier.
- A descriptive rule name.
- The declaration or condition being evaluated.
- Applicability conditions.
- Required input fields.
- Validation logic.
- The expected result.
- The relevant legal reference.
- The rule version.
- Any limitations or review requirements.

The implementation should follow the repository's existing rule-definition format.

### Rule Evaluation Sequence

A typical rule evaluation can follow this sequence:

1. Identify the rule to evaluate.
2. Determine whether its applicability conditions are satisfied.
3. Check whether required input fields are available.
4. Validate the input representation.
5. Apply the deterministic condition.
6. Produce a structured outcome.
7. Attach an explanation and supporting evidence.
8. Mark unresolved conditions for review.

A rule should not report a pass merely because its input is missing.

### Rule Versioning

Legal requirements may change through amendments, notifications, or other applicable legal instruments.

PackCheck should therefore maintain rule-version metadata wherever practical.

A rule version can record:

- The internal rule identifier.
- The applicable legal reference.
- The effective date, when verified.
- The date the rule definition was updated.
- The reason for the change.
- The test cases used to verify the implementation.

Historical reports should identify the rule version used during evaluation when that information is available.

### Rule Testing

Each deterministic rule should have test cases covering normal and abnormal inputs.

Useful test categories include:

- Valid input.
- Missing input.
- Empty input.
- Invalid format.
- Boundary values.
- Unexpected data types.
- Conflicting declarations.
- Inapplicable conditions.
- Uncertain extraction.
- Regression cases from previous defects.

Tests should validate both the outcome and the explanation associated with a finding.

---

## AI Provider Abstraction

Provider independence allows PackCheck to change its extraction backend without rewriting the compliance pipeline.

### OCRProvider Contract

The provider interface should define a consistent way to submit an image and receive a structured extraction result.

The contract may include operations for:

- Accepting image data.
- Validating supported input types.
- Requesting extraction.
- Returning structured field candidates.
- Reporting provider errors.
- Handling malformed model responses.
- Exposing relevant extraction metadata.

The precise interface must remain consistent with the application's existing implementation.

### Cloud Provider Integration

Cloud-based extraction can provide a practical starting point during development.

The planned provider configuration includes Gemini and Groq Vision APIs, subject to model availability and compatibility.

Cloud integration should account for:

- API credential management.
- Request timeouts.
- Provider rate limits.
- Response parsing.
- Temporary network failures.
- Service availability.
- Usage costs.
- External data-processing considerations.

Provider-specific response formats should be translated into the application's common extraction schema.

### Local Inference

Local inference is a planned alternative for reducing dependence on external services.

The target environment includes an NVIDIA GPU with 6 GB of VRAM, so model selection must account for memory usage, inference speed, image resolution, and extraction accuracy.

Local deployment may require compromises between:

- Model size.
- Quantization.
- Throughput.
- Latency.
- Hardware compatibility.
- Output consistency.

Local inference should be introduced through the same provider abstraction rather than by adding provider-specific branches throughout the application.

### Provider Failure Handling

If an extraction provider fails, the application should return a clear processing error.

Potential failure categories include:

- Invalid credentials.
- Network timeout.
- Rate-limit rejection.
- Unsupported image input.
- Empty response.
- Invalid structured output.
- Provider service unavailability.

Automatic retries, where implemented, should be bounded and should not create duplicate processing or uncontrolled API usage.

---

## API Design and Request Handling

The FastAPI backend provides the application boundary between the frontend and the processing services.

### Extraction Endpoint

The documented extraction endpoint is:

`POST /api/extract`

The endpoint accepts an image upload using multipart form data.

Supported image formats documented for the current workflow are:

- JPEG.
- PNG.
- WEBP.

The endpoint should validate the uploaded file before forwarding it to an extraction provider.

### Request Validation

Request validation should consider:

- Whether a file was supplied.
- Whether the file can be decoded.
- Whether the format is supported.
- Whether the file exceeds configured size limits.
- Whether the image contains usable visual information.
- Whether the request can be processed within configured resource limits.

Validation failures should produce understandable error responses.

### Response Structure

The extraction response should follow the existing Pydantic response schema.

A useful response can distinguish between:

- Extracted declarations.
- Extraction warnings.
- Processing metadata.
- Validation errors.
- Provider errors.

Compliance findings should be returned only when the compliance engine has actually evaluated the relevant rules.

The API must not invent extracted values to fill missing response fields.

### API Documentation

FastAPI provides interactive API documentation through Swagger UI when enabled.

The local development documentation is available at:

`http://127.0.0.1:8000/docs`

The documentation can be used to inspect request parameters, response schemas, and endpoint behavior.

### Health Monitoring

The health endpoint is intended to provide a simple indication that the backend is responding.

`GET /health`

A successful health response should not be interpreted as proof that every external AI provider, database, or downstream service is available.

More detailed readiness checks may be added if the application requires them.

---

## Frontend Interaction Guidelines

The React frontend provides a development interface for uploading images and inspecting extraction results.

### Image Upload Experience

The interface should make the image-processing workflow understandable.

Useful interaction elements include:

- An image-selection control.
- A preview of the selected image.
- A clear extraction action.
- A visible loading state.
- Error messages for unsuccessful requests.
- A structured presentation of returned fields.
- A way to retry after recoverable errors.

The interface should not imply that an image has been successfully processed until the backend returns a successful result.

### Results Presentation

Extraction results should be organized so that users can inspect individual declarations.

A results table can include:

- Field name.
- Extracted text.
- Normalized value, when available.
- Confidence metadata, when available.
- Validation status, when evaluated.
- Review notes, when applicable.

Missing values should be displayed explicitly rather than being confused with valid empty declarations.

### User Feedback

Frontend feedback should distinguish among:

- Upload validation errors.
- Network errors.
- Provider errors.
- Extraction warnings.
- Compliance findings.
- Successful processing.

Clear feedback makes the interface easier to test and reduces the chance of users misunderstanding an incomplete inspection.

---

## Security and Privacy Considerations

PackCheck processes package images and may communicate with external AI services.

Security and privacy should therefore be considered throughout the application lifecycle.

### API Key Protection

API credentials must remain outside source-controlled files.

Recommended practices include:

- Keeping credentials in local environment variables.
- Maintaining a sanitized `.env.example`.
- Excluding `.env` from version control.
- Avoiding API keys in frontend source code.
- Avoiding credentials in logs and error messages.
- Rotating credentials if they are accidentally exposed.

Frontend environment variables should never contain secrets that must remain private.

### Image Handling

Uploaded images should be treated as untrusted input.

Recommended safeguards include:

- Enforcing upload-size limits.
- Validating actual image content.
- Restricting accepted file formats.
- Handling malformed files safely.
- Avoiding unnecessary permanent storage.
- Limiting access to stored evidence.
- Removing temporary files when appropriate.

### External AI Services

When cloud extraction is enabled, image data may be transmitted to the configured provider.

The deployment documentation should identify which provider is used and what data is sent.

Before production use, the team should review the provider's applicable data-retention, privacy, and security terms.

### Logging

Logs should support debugging without unnecessarily exposing sensitive information.

Useful log fields may include:

- Request identifier.
- Processing stage.
- Provider identifier.
- Execution duration.
- Error category.
- Success or failure status.

API keys, authentication tokens, and other secrets must not be written to logs.

### Error Handling

Errors returned to clients should provide enough information to resolve common issues without exposing internal stack traces, credentials, or implementation details.

Detailed diagnostic information should remain in appropriately protected development logs.

---

## Testing Strategy

PackCheck benefits from testing at multiple levels because extraction quality and legal decision correctness are different concerns.

### Unit Tests

Unit tests should validate individual functions and services independently.

Examples include:

- Image input validation.
- Field normalization.
- Date parsing.
- Quantity parsing.
- Rule evaluation.
- Error conversion.
- Response serialization.

These tests should avoid unnecessary external dependencies.

### Provider Tests

Provider tests should verify that each implementation follows the shared provider contract.

Mock responses can be used to test:

- Successful extraction.
- Missing fields.
- Unexpected response formats.
- Invalid JSON responses.
- Provider timeouts.
- Authentication errors.
- Rate-limit errors.

### API Integration Tests

Integration tests should verify the interaction between the API layer and its underlying services.

Relevant cases include:

- Valid image upload.
- Unsupported file format.
- Missing file.
- Malformed image.
- Provider failure.
- Successful structured response.
- Correct HTTP status codes.
- Expected error-response structure.

### End-to-End Tests

End-to-end tests can validate the complete workflow from image submission to result presentation.

A representative workflow includes:

1. Select a sample package image.
2. Submit the image to the backend.
3. Validate the request.
4. Obtain an extraction response.
5. Evaluate configured rules, where integrated.
6. Display the result.
7. Verify that errors and warnings remain visible.

### Regression Testing

Whenever a bug is fixed, add a regression test where practical.

Regression tests help ensure that changes to extraction parsing, rule definitions, or response schemas do not reintroduce previously resolved defects.

### Mocked Dependencies

The existing backend test workflow uses mocked providers and mocked Gemini responses.

This makes it possible to test application behavior without requiring a live API key or network connection for those tests.

Mocked tests do not establish the accuracy of a live AI provider. Provider accuracy should be assessed separately using representative package images and verified reference annotations.

---

## Evaluation and Quality Metrics

PackCheck should be evaluated using measurable criteria rather than relying only on successful demonstrations.

### Extraction Metrics

Potential extraction metrics include:

- Field-level accuracy.
- Exact-match rate.
- Character error rate.
- Word error rate.
- Missing-field detection rate.
- Numerical extraction accuracy.
- Date extraction accuracy.

Metrics should be calculated using annotated reference data and clearly documented evaluation rules.

### Compliance Metrics

Useful compliance metrics include:

- Rule-level accuracy.
- False-positive rate.
- False-negative rate.
- Review-required rate.
- Correct handling of inapplicable rules.
- Completeness of supporting evidence.
- Consistency of repeated evaluations.

A false positive occurs when the system flags a compliant condition as a violation. A false negative occurs when the system fails to identify a genuine violation.

Both error types matter, especially when users rely on findings to prioritize inspections.

### Dataset Quality

Evaluation data should include diverse package layouts, lighting conditions, printing styles, and image quality levels.

The dataset may contain:

- Clear package images.
- Low-resolution images.
- Rotated images.
- Partially obscured declarations.
- Small printed text.
- Multiple labels on a package.
- Similar-looking numerical characters.
- Representative compliant examples.
- Representative non-compliant examples.

Synthetic defects can supplement real-world examples, but synthetic examples should be clearly identified and should not be treated as a complete substitute for representative real-world data.

### Human Review Metrics

Human review can be evaluated using:

- Agreement between reviewers.
- Frequency of corrected extractions.
- Frequency of overridden rule outcomes.
- Time required to resolve uncertain cases.
- Common reasons for review.

These metrics can guide improvements to image quality checks, extraction prompts, normalization logic, and rule definitions.

---

## Dataset and Sample Management

The `data/` directory is intended to hold development samples and defect-oriented test material.

### Sample Organization

Package images should be organized so that developers can identify their purpose without inspecting every file manually.

Useful metadata includes:

- Sample identifier.
- Commodity category.
- Image source.
- Expected extraction fields.
- Expected rule outcomes.
- Known defects.
- Annotation status.
- Dataset version.

### Seeded Defects

Seeded defects provide controlled examples for evaluating validation logic.

Examples might include:

- A missing expected declaration.
- An incorrectly formatted quantity.
- An ambiguous date.
- An inconsistent extracted value.
- A partially obscured label.
- A missing consumer-information field, where required.

Each seeded defect should identify the intended test condition and the expected system behavior.

### Dataset Integrity

Sample data should be kept separate from application secrets and unrelated personal information.

The team should also record any usage restrictions associated with externally sourced images.

### Reproducible Evaluation

Evaluation runs should record the dataset version and relevant application or rule version.

This helps explain differences in results after changes to the extraction provider, preprocessing pipeline, or statutory rules.

---

## Performance and Reliability

The application should remain responsive and predictable as package images and processing workloads vary.

### Processing Time

Potential contributors to latency include:

- Image decoding.
- Image preprocessing.
- External API requests.
- Local model inference.
- Response parsing.
- Rule evaluation.
- Report generation.

Performance measurements should separate these stages where possible.

### Resource Management

The backend should avoid loading unnecessarily large images or retaining uploaded data longer than required.

For local inference, memory use should be monitored against the available GPU and system RAM.

### Timeouts

External provider calls should use appropriate timeouts.

An indefinitely waiting request can consume server resources and degrade the user experience.

### Reliability

Reliability improvements may include:

- Structured exception handling.
- Bounded retries.
- Clear failure categories.
- Request identifiers.
- Resource cleanup.
- Health checks.
- Regression tests.

Retries should be used only when the failure is plausibly transient and the operation can be safely repeated.

### Graceful Degradation

If an optional extraction provider is unavailable, the system should communicate the failure clearly.

The application must not generate a fabricated compliance result as a substitute for a failed extraction.

If the architecture later supports multiple providers, any fallback should be explicit, observable, and consistent with the provider contract.

---

## Development Conventions

Consistent development practices make PackCheck easier to maintain and extend.

### Python Code

Python code should follow the conventions already established in the backend.

Recommended practices include:

- Meaningful function and variable names.
- Type annotations for important interfaces.
- Small, focused service functions.
- Clear exception handling.
- Reusable validation logic.
- Explicit data models.
- Avoidance of duplicated statutory logic.

### React Code

Frontend components should have clear responsibilities.

For example, upload controls, request handling, and result presentation can be separated as the interface grows.

Avoid duplicating API request logic across unrelated components.

### Configuration

Application configuration should be centralized where practical.

Environment-specific values should not be scattered throughout the codebase.

Default configuration should be safe for local development and should not expose sensitive information.

### Documentation

When a new endpoint, provider, rule family, or configuration option is introduced, the relevant documentation should be updated.

Documentation should describe actual behavior and clearly identify planned features.

---

## Troubleshooting Guide

This section covers common development issues and practical checks.

### Backend Does Not Start

Possible causes include:

- Python is not installed or is not on PATH.
- The virtual environment is not activated.
- Dependencies are missing.
- The import path is incorrect.
- The configured port is already in use.

Suggested checks:

1. Confirm the Python version.
2. Activate the virtual environment.
3. Install backend requirements.
4. Review the terminal traceback.
5. Confirm the expected working directory.
6. Check whether port `8000` is available.

### Frontend Does Not Start

Possible causes include:

- Node.js or npm is unavailable.
- Dependencies were not installed.
- The package scripts are missing or incorrect.
- Port `5173` is already occupied.

Suggested checks:

1. Run `node --version`.
2. Run `npm --version`.
3. Navigate to `frontend/`.
4. Run `npm install`.
5. Run `npm run dev`.
6. Inspect the terminal output for errors.

### Frontend Cannot Reach the Backend

Check that:

- The backend process is running.
- The backend URL is correct.
- The health endpoint responds.
- CORS settings permit the frontend origin.
- The frontend is using the intended API address.
- No network or local security rule is blocking the request.

A successful frontend build does not guarantee that the backend connection is configured correctly.

### API Key Errors

If cloud extraction fails:

1. Confirm that the correct environment file is loaded.
2. Verify that the API key is present.
3. Check whether the key is valid and enabled.
4. Confirm that the selected model is available.
5. Review provider-specific error messages.
6. Check applicable quota and rate limits.

Never paste API credentials into issue reports or commit them to the repository.

### Extraction Results Are Incomplete

Possible causes include:

- Low image resolution.
- Glare or shadows.
- Small printed text.
- Rotated or distorted labels.
- Provider response limitations.
- Incorrect response parsing.
- Missing declarations on the visible package surface.

Compare the extracted values with the original image before deciding whether the issue originates in OCR, normalization, or rule evaluation.

### Tests Fail

When a test fails:

1. Read the first relevant assertion failure.
2. Identify whether the failure is in a unit, provider, or integration test.
3. Inspect recent changes to the affected component.
4. Check fixtures and mocked responses.
5. Re-run the failing test independently.
6. Run the broader suite after correcting the issue.

Do not weaken a test simply to make it pass without understanding the intended behavior.

---

## Suggested Development Roadmap

The following roadmap describes possible improvements. It is not a statement that every feature has already been implemented.

### Phase 1: Core Extraction

- Stabilize the upload endpoint.
- Standardize extraction response schemas.
- Improve input validation.
- Add representative extraction tests.
- Document provider configuration.
- Establish a repeatable local development workflow.

### Phase 2: Deterministic Validation

- Define structured statutory rules.
- Add field normalization utilities.
- Implement applicability checks.
- Add rule-level tests.
- Standardize compliance findings.
- Connect extracted fields to rule inputs.

### Phase 3: Evidence Traceability

- Associate findings with extracted fields.
- Preserve original declaration text.
- Use bounding boxes when available.
- Record rule identifiers and versions.
- Improve reviewer access to supporting evidence.
- Distinguish missing evidence from failed compliance.

### Phase 4: Human Review

- Identify uncertain extraction results.
- Present unresolved fields clearly.
- Record review decisions where supported.
- Track corrections for evaluation.
- Add tests for ambiguous cases.

### Phase 5: Provider Independence

- Validate the shared OCRProvider contract.
- Standardize provider error handling.
- Evaluate cloud provider consistency.
- Benchmark local inference.
- Compare accuracy and latency.
- Document fallback behavior if implemented.

### Phase 6: Evaluation and Reporting

- Expand the annotated sample dataset.
- Establish extraction quality metrics.
- Measure rule-level performance.
- Add regression tests for known defects.
- Improve report structure.
- Document limitations and evaluation methodology.

### Phase 7: Deployment Readiness

- Review secret management.
- Add appropriate upload limits.
- Improve logging and diagnostics.
- Test failure handling.
- Document deployment configuration.
- Review privacy and security requirements.

---

## Known Limitations and Responsible Use

PackCheck is a software-assisted compliance checking project, and its conclusions depend on the evidence and rules available to it.

### Image-Based Limitations

A photograph may not show every side of a package.

Declarations may be hidden, folded, damaged, too small to read, or outside the captured frame.

A single image should not be assumed to represent the complete physical package.

### Extraction Limitations

AI and OCR systems can misread text, numbers, symbols, and units.

Extracted values should be verified when uncertainty affects the outcome.

### Legal Interpretation Limitations

Legal requirements may depend on product category, exemptions, package characteristics, and applicable amendments.

Software rules should be reviewed against authoritative legal sources before being relied upon in operational inspections.

### Scope Limitations

A successful check of selected declarations does not establish that a package satisfies every applicable legal obligation.

Reports should identify the checks actually performed and any conditions that remain unevaluated.

### Human Oversight

PackCheck is intended to assist inspection and review workflows.

Where uncertainty, legal interpretation, or incomplete evidence affects a conclusion, human review remains important.

The application should communicate its limitations clearly and should not claim official certification or enforcement authority unless such status has been independently established.

---

## Contribution Guidelines

Contributions should improve correctness, maintainability, usability, or test coverage.

### Before Opening a Pull Request

- Review the current implementation.
- Identify the affected module.
- Keep changes focused on the intended task.
- Add or update tests.
- Update documentation where necessary.
- Check that secrets and temporary files are excluded.
- Run relevant backend tests.
- Run frontend validation and build commands when applicable.

### Pull Request Description

A useful pull request description should include:

- Purpose of the change.
- Components affected.
- Important implementation details.
- Tests performed.
- Known limitations.
- Any configuration changes.
- Any statutory references affected.

### Statutory Rule Contributions

Changes to legal rules require additional care.

Contributors should identify the relevant authoritative source, explain the intended applicability conditions, and include test cases covering expected and exceptional inputs.

Unverified legal assumptions should not be presented as established requirements.

---

## Frequently Asked Questions

### Does PackCheck use AI to decide legal compliance?

No. The architectural principle separates AI-assisted extraction from deterministic compliance decisions. AI proposes extracted information, while configured rules evaluate the available data.

### Can PackCheck process every type of packaged commodity?

The supported scope depends on the declarations, rule definitions, and applicability logic implemented in the application. Coverage should not be assumed for commodity categories that have not been evaluated.

### Does an extraction result guarantee that a declaration is correct?

No. Extraction results may contain errors and should be checked against the source image when necessary.

### Does a passing result guarantee full legal compliance?

No. A pass applies to the conditions that were actually evaluated. Other requirements may remain outside the current inspection scope.

### Can PackCheck work without a cloud API?

The architecture is intended to support local inference through a provider abstraction. Actual offline operation depends on whether a compatible local provider has been implemented and configured.

### Are API keys required to run every test?

The documented backend test suite uses mocked providers and mocked Gemini responses, so those tests do not require a live API key or network access.

### Why are some fields marked for review?

A field may require review because its extraction is uncertain, its value is missing, its interpretation is ambiguous, or a definitive rule outcome cannot be established from the available evidence.

### Can new statutory rules be added?

The rules directory is intended to hold deterministic compliance rule definitions. New rules should follow the existing implementation pattern and include appropriate tests and authoritative references.

### How can extraction accuracy be improved?

Use representative package images, inspect incorrect predictions, improve input quality, refine provider prompts or preprocessing where appropriate, and measure performance against annotated reference data.

### How should a reported violation be investigated?

Review the original image, extracted declaration, associated rule, rule version, validation explanation, and any uncertainty warnings before reaching a final conclusion.

---

## Glossary

| Term | Meaning |
| :--- | :--- |
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| OCR | Optical Character Recognition |
| DTO | Data Transfer Object |
| MRP | Maximum Retail Price |
| FastAPI | Python web framework used for the backend |
| React | JavaScript library used for the frontend |
| Vite | Frontend development and build tool |
| Pydantic | Python data validation and settings library |
| CORS | Cross-Origin Resource Sharing |
| CI | Continuous Integration |
| Regression Test | A test that checks previously established behavior |
| Bounding Box | Coordinates identifying a region of an image |
| Normalization | Converting a value into a consistent structured representation |
| False Positive | An incorrect violation finding |
| False Negative | A missed violation |
| Human-in-the-Loop | A workflow in which people review or resolve selected decisions |
| Deterministic Rule | A rule that produces a defined outcome from the same inputs and configuration |
| Evidence Traceability | The ability to connect a finding to its supporting source information |
| Provider Abstraction | A common interface that separates application logic from a specific service provider |

---

## Project Principles

PackCheck follows several principles intended to guide future development.

1. **Evidence first:** Findings should be supported by available package evidence.
2. **Separation of concerns:** Extraction, validation, review, and reporting should remain distinct responsibilities.
3. **Deterministic decisions:** Statutory checks should use explicit, testable rules.
4. **Transparent uncertainty:** Missing or ambiguous information should remain visible.
5. **Provider independence:** Application logic should not depend unnecessarily on one AI provider.
6. **Reproducibility:** Tests and evaluation datasets should support repeatable results.
7. **Security by design:** Credentials and uploaded data should be handled responsibly.
8. **Human oversight:** Uncertain or context-dependent findings should be reviewable.
9. **Maintainability:** New capabilities should fit the existing modular architecture.
10. **Responsible claims:** Documentation and reports should describe the system's actual capabilities and limitations.

---

## Final Note

PackCheck is designed to make packaged-commodity compliance inspection more structured, explainable, and evidence-driven.

By combining image-based extraction, deterministic statutory validation, human review, and traceable results, the project aims to reduce repetitive manual checking while preserving transparency about uncertainty and limitations.

The long-term objective is to build a maintainable compliance-assistance platform in which every automated finding can be understood, evaluated, and traced back to the available evidence and the applicable rule definition.

**Core principle:** Extract accurately. Validate deterministically. Review uncertainty. Report with evidence.
