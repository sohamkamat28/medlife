# MedLife

MedLife is a Dash web app for analyzing medical report text or report images. It extracts text with OCR, identifies patient names and medical entities using Transformer NER models, and shows simplified definitions from a medical glossary CSV.

## Features

- Text input for pasted medical report content.
- Image upload with OCR extraction through Tesseract.
- Biomedical named-entity recognition using `d4data/biomedical-ner-all`.
- Patient name detection using `dslim/bert-base-NER`.
- Glossary-backed definitions displayed in a searchable Dash table.

## Interface and delivery

- Server-rendered marketing shell so the headline and hero image appear before the Dash client bundle finishes loading.
- Responsive, locally hosted WebP hero imagery with explicit dimensions to prevent layout shift.
- Self-hosted Geist variable font, system-aware light and dark themes, keyboard focus states, and reduced-motion support.
- Custom empty, loading, warning, error, and successful results states.
- Search metadata, Open Graph tags, a sitemap, `robots.txt`, and `llms.txt` for discovery.

## Project Structure

- `app.py` - Dash UI and callbacks.
- `ocr_handler.py` - OCR helper using `pytesseract`.
- `ner_model.py` - Transformer NER model loading and entity cleanup.
- `data_handler.py` - Glossary CSV loading and definition lookup.
- `medical_glossary_large 2.csv` - Main glossary used by the app.
- `medical_glossary.csv` and `updated_medical_terms 2.csv` - Additional glossary/reference data.
- `test/` - Sample report image snippets.

## Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

For the full local ML version with Transformer NER models:

```bash
pip install -r requirements-full.txt
```

Install the Tesseract executable separately:

```bash
brew install tesseract
```

If Tesseract is installed somewhere other than your system path, set:

```bash
export TESSERACT_CMD=/path/to/tesseract
```

Run the app:

```bash
python app.py
```

The first run may take time because the Transformer models are downloaded by `transformers`.

## Deploying on Vercel

This repository includes `vercel.json` for Vercel deployment. Vercel serverless functions have a strict bundle-size limit, so the default `requirements.txt` intentionally excludes `torch` and `transformers`.

On Vercel, MedLife runs with glossary-backed text analysis and disables the heavy Transformer models through:

```bash
MEDLIFE_ENABLE_TRANSFORMERS=0
```

For full Transformer accuracy, run locally or deploy to a platform with larger containers such as Render, Railway, or a VPS.
