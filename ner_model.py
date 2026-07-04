import re
from typing import List, Tuple

from transformers import pipeline

from data_handler import find_glossary_terms, normalize_term


try:
    med_ner_model = pipeline("ner", model="d4data/biomedical-ner-all", grouped_entities=True)
except Exception as e:
    print(f"Error loading biomedical NER model: {e}. Falling back to empty list.")
    med_ner_model = lambda text: []

try:
    name_ner_model = pipeline("ner", model="dslim/bert-base-NER", grouped_entities=True)
except Exception as e:
    print(f"Error loading name NER model: {e}. Falling back to empty list.")
    name_ner_model = lambda text: []


def _clean_entity_word(word: str) -> str:
    cleaned = str(word).replace(" ##", "").replace("##", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;|/\\")
    return cleaned.strip()


def _run_model(model, text: str) -> list[dict]:
    try:
        results = model(text)
        return results if isinstance(results, list) else []
    except Exception as e:
        print(f"NER model failed during analysis: {e}")
        return []


def _extract_patient_name(text: str) -> str:
    name_results = _run_model(name_ner_model, text)

    for result in name_results:
        if result.get("entity_group") == "PER":
            name_candidate = _clean_entity_word(result.get("word", ""))
            if len(name_candidate) > 2:
                return name_candidate

    label_patterns = [
        r"(?:patient\s*name|patient|name)\s*[:\-]\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})",
        r"(?:pt\.?\s*name)\s*[:\-]\s*([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,3})",
    ]

    for pattern in label_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _clean_entity_word(match.group(1))
            if len(candidate) > 2:
                return candidate

    return ""


def _merge_adjacent_entities(text: str, staged_results: list[dict]) -> list[tuple[str, str]]:
    merged_results = []
    i = 0

    while i < len(staged_results):
        current = staged_results[i]
        merged_word = current["word"]
        current_label = current["label"]
        j = i + 1

        while j < len(staged_results) and staged_results[j]["label"] == current_label:
            previous_end = staged_results[j - 1].get("end")
            next_start = staged_results[j].get("start")

            if isinstance(previous_end, int) and isinstance(next_start, int):
                gap = text[previous_end:next_start]
                if len(gap) > 2 or re.search(r"[,;:\n]", gap):
                    break
                separator = " " if gap.strip() else ""
            else:
                current_short = len(staged_results[j - 1]["word"]) <= 4
                next_short = len(staged_results[j]["word"]) <= 4
                if not (current_short and next_short):
                    break
                separator = ""

            merged_word += separator + staged_results[j]["word"]
            j += 1

        merged_results.append((merged_word, current_label))
        i = j

    return merged_results


def analyze_text(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Analyze report text using patient-name NER, biomedical NER, and glossary matching.
    Returns (patient_name, list of medical entities).
    """
    if not text:
        return "", []

    patient_name = _extract_patient_name(text)
    med_results = _run_model(med_ner_model, text)
    staged_results = []

    for result in med_results:
        label = str(result.get("entity_group", "")).split("-")[-1]
        word = _clean_entity_word(result.get("word", ""))

        if not word:
            continue

        if label in ["LOC", "ORG", "MISC", "PER"] or word.lower() == patient_name.lower():
            continue

        staged_results.append({
            "word": word,
            "label": label or "Medical Term",
            "start": result.get("start"),
            "end": result.get("end"),
        })

    glossary_results = find_glossary_terms(text)
    model_results = _merge_adjacent_entities(text, staged_results)

    processed_results = []
    seen_entities = set()

    for word, label in glossary_results + model_results:
        normalized = normalize_term(word)

        if normalized and normalized not in seen_entities:
            processed_results.append((word, label))
            seen_entities.add(normalized)

    return patient_name, processed_results
