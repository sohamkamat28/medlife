import os
import re
from difflib import get_close_matches

import pandas as pd

# --- Global Glossary Lookup Table ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLOSSARY_FILE = os.path.join(BASE_DIR, 'medical_glossary_large 2.csv')
GLOSSARY_DATA = {}
GLOSSARY_TERMS = []
DEFINITION_NOT_FOUND = "Glossary data not loaded." # Use the original error message for consistency


def normalize_term(term: str) -> str:
    """Normalize glossary and extracted terms for reliable matching."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", str(term).lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _singular_variants(term: str) -> list[str]:
    variants = [term]

    if term.endswith("ies") and len(term) > 4:
        variants.append(f"{term[:-3]}y")
    if term.endswith("es") and len(term) > 3:
        variants.append(term[:-2])
    if term.endswith("s") and len(term) > 3:
        variants.append(term[:-1])

    return variants

def load_glossary():
    """Loads the glossary CSV into a global dictionary for fast lookup."""
    global GLOSSARY_DATA, GLOSSARY_TERMS

    if not os.path.exists(GLOSSARY_FILE):
        print(f"ERROR: Glossary file not found at {GLOSSARY_FILE}. Definitions will fail.")
        return

    try:
        df = pd.read_csv(GLOSSARY_FILE)
        glossary = {}

        for _, row in df.iterrows():
            entity = str(row.get('Entity', '')).strip()
            definition = str(row.get('Definition', '')).strip()

            if not entity or not definition or definition.lower() == 'nan':
                continue

            key = normalize_term(entity)
            if key:
                glossary[key] = {
                    "entity": entity,
                    "definition": definition,
                }

        GLOSSARY_DATA = glossary
        GLOSSARY_TERMS = sorted(
            glossary.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        print(f"Successfully loaded {len(GLOSSARY_DATA)} glossary entries.")

    except Exception as e:
        print(f"An error occurred loading the glossary: {e}")
        GLOSSARY_DATA = {}
        GLOSSARY_TERMS = []

# Load the glossary immediately when the file is imported
load_glossary()

def resolve_definition(word: str, allow_fuzzy: bool = True) -> dict | None:
    """Return the glossary record for a term, including tolerant OCR variants."""
    normalized_word = normalize_term(word)
    if not normalized_word:
        return None

    for candidate in _singular_variants(normalized_word):
        if candidate in GLOSSARY_DATA:
            return GLOSSARY_DATA[candidate]

    compact_word = normalized_word.replace(" ", "")
    for key, record in GLOSSARY_DATA.items():
        if key.replace(" ", "") == compact_word:
            return record

    if allow_fuzzy and len(normalized_word) >= 6:
        matches = get_close_matches(normalized_word, GLOSSARY_DATA.keys(), n=1, cutoff=0.92)
        if matches:
            return GLOSSARY_DATA[matches[0]]

    return None


def find_glossary_terms(text: str) -> list[tuple[str, str]]:
    """Find known glossary terms directly in report text."""
    if not text or not GLOSSARY_TERMS:
        return []

    matches = []
    occupied_spans = []

    for key, record in GLOSSARY_TERMS:
        if len(key) < 3:
            continue

        escaped_parts = [re.escape(part) for part in key.split()]
        pattern = r"(?<![A-Za-z0-9])" + r"[\s\-/]+".join(escaped_parts)
        if key[-1].isalnum():
            pattern += r"s?"
        pattern += r"(?![A-Za-z0-9])"

        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            span = match.span()
            if any(span[0] < used[1] and span[1] > used[0] for used in occupied_spans):
                continue

            occupied_spans.append(span)
            matches.append((record["entity"], "Glossary Match"))

    return matches


def get_definition(word: str) -> str:
    """
    Retrieves the simple definition for a given word.

    Args:
        word: The medical entity extracted by the NER model.

    Returns:
        The corresponding definition string, or a failure message.
    """
    record = resolve_definition(word)

    if record:
        return record["definition"]

    return DEFINITION_NOT_FOUND
