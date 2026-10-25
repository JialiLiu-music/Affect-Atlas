# Manuscript delivery and review status

## Files

- Main draft: `../manuscript_en.md` (419 lines, complete English first draft).
- Browser-readable version: `../manuscript_en.html`.
- Editable Word version: `../manuscript_en.docx`.
- Evidence map: `evidence_map.md`.
- Chapter blueprint: `chapter_blueprint.md`.
- Figure generator: `../scripts/generate_figures.py`.
- Manuscript audit: `../scripts/audit_manuscript.py`.
- Output builder: `../scripts/build_manuscript_outputs.py`.

## Scope

This is a complete first draft, not a venue-specific camera-ready submission. It foregrounds the prespecified PMEmo result and retains only negative or uncertain evidence that changes the interpretation of the main claim. It omits unrelated abandoned dynamic/projection experiments from the main narrative.

## Verified contents

- 14 references are present, cited bidirectionally, and independently citation-checked as VERIFIED by a fresh-context verifier.
- 6 figures are embedded by relative path; vector PDF/SVG and 300-dpi PNG variants already exist.
- 8 quantitative tables include source baselines, data roles, all external methods/budgets, primary metrics, stability, genre development and DEAM expansion.
- Main primary result: ten-rating arousal-only half-offset, PMEmo arousal MSE 0.130907451 to 0.113240858; delta -0.017666593; conditional group-bootstrap 95% interval [-0.020519108, -0.014643378].
- The numerical audit reports 40,650 checks, 291,626 numerical comparisons and maximum discrepancy 8.88e-16. The independent server-side NumPy head replay reports maximum prediction difference 1.06e-7.
- `audit_manuscript.py` passes: 419 lines, 14 references, 6 figures, 8 tables, no placeholder markers.
- The source figure manifest reports a maximum reconstruction error of 8.74e-16 and unchanged source hashes.

## Before submission

- Replace the title if the target journal requires a shorter title.
- Add author names, affiliations, corresponding-author information, funding and conflict-of-interest statements supplied by the authors.
- Select a journal and convert the manuscript to its required template and reference style.
- Decide whether the journal requires a formal data/code availability statement. Do not promise redistribution of commercial audio.
- Consider adding a matched implementation of prior personalization/adaptation methods only if the target journal requires stronger method-level comparison; this is not needed to complete the current first draft.
- A final journal-specific statistical and ethics review remains separate from this first-draft audit.
