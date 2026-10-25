# Low-Label Output Calibration for Music Emotion Regression

A draft paper on few-shot, cross-dataset output calibration for music emotion regression, with accompanying figures and supporting materials.

## Reading Guide

- [English manuscript](manuscript_en.md)
- [HTML version](manuscript_en.html) (GitHub displays the source; download the repository and open it locally to read)
- [Editable Word version](manuscript_en.docx)
- [Figures and captions](figures/captions.md)
- [Literature evidence records](working/literature_evidence.json)

## Research Overview

Using frozen MERT music representations and an emotion prediction head trained on DEAM, this study compares output calibration with labeling budgets of 5 or 10 songs on complete PMEmo choruses. In the prespecified primary comparison, calibration with 10 labeled songs and a half-strength offset applied only to arousal reduced arousal mean squared error by an average of 13.50% across 334 fixed evaluation risk-group representatives. The manuscript and appendices document dataset roles, full comparisons, adaptation-pool stability, and the scope of the conclusions.

The manuscript is currently an English-language draft. Author information, the target journal template, and formal submission declarations remain to be added.

## CPU Music Emotion Demo

The demo source is available in [`code/`](code/README.md), with a React/TypeScript frontend in Chinese and a separate FastAPI CPU backend. It supports audio clip uploads, overall valence–arousal predictions, exploratory scores with 10-second windows and a 5-second hop, playback synchronization, and JSON/CSV export. The window curves come from a static model and do not represent validated second-by-second dynamic emotion recognition. Target-domain calibration is disabled by default.

See [`code/README.md`](code/README.md) for startup instructions, the pinned MERT download, and verification of the paper's prediction head. Model weights, sample music, virtual environments, and `node_modules` are excluded from the repository; real model assets must be prepared after cloning. The scope of automated tests and real CPU execution checks is documented in [`code/VALIDATION.md`](code/VALIDATION.md) and [`code/TIMELINE_UPGRADE-20261012.md`](code/TIMELINE_UPGRADE-20261012.md). Publishing the source code does not deploy a publicly accessible website.

## Repository Structure

- `manuscript_en.*`: Manuscript in Markdown, HTML, and Word formats.
- `figures/`: Six figures in PNG/PDF/SVG formats, captions, and a source-verification manifest.
- `scripts/`: Scripts for figure generation, manuscript structure checks, and document export.
- `working/`: Evidence maps, literature records, chapter blueprints, and revision notes.

## Scripts

Run `python scripts/audit_manuscript.py` from the repository root to check manuscript structure and file references.

Run `python scripts/build_manuscript_outputs.py` to regenerate HTML and Word files from Markdown. Install the dependencies first with `python -m pip install -r scripts/requirements-documents.txt` (Python 3.10 or later). HTML renders equations offline using native MathML and is suitable for modern Chrome, Edge, or Firefox. Word export uses Pandoc to create editable native equation objects. Markdown uses GitHub-supported `$...$` and `$$...$$` math delimiters.

Run `python scripts/test_math_rendering.py` to verify the 10 standalone equations, inline equations, and Word equation structure, and to check that mathematical expressions are unchanged from the original commit. Run `python scripts/test_reporting_integrity.py` to check that the full results tables, appendices, references, and required limitations remain consistent before and after revisions to the contribution wording. GitHub's source view displays HTML code; open the HTML locally to read it. For Markdown, use the rendered view rather than the Raw source.

Figure generation requires `numpy`, `matplotlib`, and experiment JSON files from the original workspace's `进度/` directory. Complete raw experiment artifacts, model weights, music audio, and locally installed dependencies are excluded from this repository. The `figure_manifest.json` file records source paths and SHA checksums; its presence does not mean that the complete experimental data have been publicly released.

Commercial song audio is not distributed with this repository. See the manuscript and references for dataset and model sources.
