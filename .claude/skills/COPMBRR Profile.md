---
name: COPMBRR-Profile
description: Use when asked to create, build, or generate a COPMBRR profile or summary JSON for a studied COPMBRR document.
---

# COPMBRR Profile Creator

## Overview

Creates a structured JSON profile file for a studied COPMBRR (Congestion Offset Payment Mechanism Bilateral Revision Request), capturing all key metadata fields extracted from the COPMBRR documents. The output file is saved under the COPMBRR's own folder in a `Quick runs` sub-folder.

## Output Location

```
Documents Database/ERCOT.MKT.RULES/COPMBRR/COPMBRR<number>/Quick runs/COPMBRR<number> Profile.json
```

- Create the `Quick runs` sub-folder if it does not already exist.
- File name format: `COPMBRR<number> Profile.json` — e.g. `COPMBRR015 Profile.json`.

## Profile Fields

Extract the following fields from the COPMBRR documents. Use `null` for any field not found.

| # | JSON Key | Source |
|---|----------|--------|
| 1 | `copmbrr_number` | COPMBRR number (integer) |
| 2 | `title` | Full title of the revision request |
| 3 | `date_posted_decision` | Date Posted or Decision date (ISO 8601: YYYY-MM-DD) |
| 4 | `timeline_requested_resolution` | Requested Resolution date or milestone |
| 5 | `status` | Current status (Pending / Approved / Withdrawn) |
| 6 | `effective_date` | Effective date of the revision (ISO 8601 or null) |
| 7 | `agreement_sections_requiring_revision` | Array of COPM Bilateral agreement section identifiers |
| 8 | `related_documents_requiring_revision` | Array of related document names or IDs |
| 9 | `revision_description` | Plain-text summary of what is being revised |
| 10 | `reason_for_revision` | Why the revision is needed |
| 11 | `business_case` | Business justification or impact statement |
| 12 | `sponsor_name` | Full name of the sponsor |
| 13 | `sponsor_email` | Sponsor email address |
| 14 | `sponsor_company` | Sponsor's organization or company |
| 15 | `sponsor_phone` | Sponsor phone number (string) |
| 16 | `market_segment` | Market segment(s) affected (string or array) |

## JSON Template

```json
{
  "copmbrr_number": null,
  "title": null,
  "date_posted_decision": null,
  "timeline_requested_resolution": null,
  "status": null,
  "effective_date": null,
  "agreement_sections_requiring_revision": [],
  "related_documents_requiring_revision": [],
  "revision_description": null,
  "reason_for_revision": null,
  "business_case": null,
  "sponsor_name": null,
  "sponsor_email": null,
  "sponsor_company": null,
  "sponsor_phone": null,
  "market_segment": null
}
```

## Steps

1. Identify the COPMBRR number from the user's request or from the document file names.
2. Read the primary COPMBRR document (e.g. `*COPMBRR-01 *.docx`) and any supporting documents in the `COPMBRR<number>/` folder.
3. Extract all 16 fields. For multi-value fields (`agreement_sections_requiring_revision`, `related_documents_requiring_revision`), produce a JSON array.
4. Normalize dates to ISO 8601 (`YYYY-MM-DD`). Leave as a descriptive string if only a milestone name is available.
5. Ensure `Quick runs/` sub-folder exists under `Documents Database/ERCOT.MKT.RULES/COPMBRR/COPMBRR<number>/`.
6. Write the JSON file to `Quick runs/COPMBRR<number> Profile.json` with 2-space indentation.
7. Report the saved file path and list any fields that could not be populated.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Saving the file in the wrong folder | Always use `COPMBRR<number>/Quick runs/`, not the COPMBRR root or project root |
| Using the wrong file name | Must be `COPMBRR<number> Profile.json`, not `profile.json` or `COPMBRRProfile.json` |
| Leaving dates as raw text | Normalize to `YYYY-MM-DD`; use string only when no calendar date is available |
| Omitting empty arrays | Use `[]` for array fields with no data, never omit the key |
