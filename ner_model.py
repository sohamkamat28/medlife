from transformers import pipeline
from typing import List, Tuple

# Biomedical Model (for Drug, Disease, Procedure, etc.)
try:
    med_ner_model = pipeline("ner", model="d4data/biomedical-ner-all", grouped_entities=True)
except Exception as e:
    print(f"Error loading biomedical NER model: {e}. Falling back to empty list.")
    med_ner_model = lambda text: []

try:
    # dslim/bert-base-NER is excellent at identifying general Person names ('PER')
    name_ner_model = pipeline("ner", model="dslim/bert-base-NER", grouped_entities=True)
except Exception as e:
    print(f"Error loading name NER model: {e}. Falling back to empty list.")
    name_ner_model = lambda text: []


# --- 2. Combined Analysis Function ---

def analyze_text(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Analyzes text using two NER models: one for names (PER) and one for medical terms.
    Returns (patient_name, list of medical entities).
    """
    if not text:
        return "", []

    patient_name = ""

    # --- 2a. NAME EXTRACTION ---
    name_results = name_ner_model(text)

    for r in name_results:
        if r["entity_group"] == "PER":
            name_candidate = r["word"].replace(" ##", "").replace("##", "").strip()

            if len(name_candidate) > 2 and name_candidate.count(' ') > 0:
                patient_name = name_candidate
                break

    # --- 2b. MEDICAL TERM EXTRACTION & MERGING ---
    med_results = med_ner_model(text)

    # Stage 1: Initial cleanup and staging the results
    staged_results = []

    for r in med_results:
        label = r["entity_group"].split('-')[-1]

        # Robust word reassembly for fragmented tokens (e.g., removing '##')
        word = r["word"].replace(" ##", "").replace("##", "").strip()

        # Skip general NER tags and patient name
        if label in ["LOC", "ORG", "MISC", "PER"] or word.lower() == patient_name.lower():
             continue

        # Add to staged results list
        staged_results.append({'word': word, 'label': label})


    # Stage 2: Aggressive Consecutive Merge (Fixes Li, Sin, Opril -> Lisinopril)
    final_merged_results = []
    i = 0
    while i < len(staged_results):
        current = staged_results[i]
        merged_word = current['word']
        current_label = current['label']
        j = i + 1

        # Look ahead for consecutive entities with the same label
        while j < len(staged_results) and staged_results[j]['label'] == current_label:
            merged_word += staged_results[j]['word']
            j += 1

        final_merged_results.append((merged_word, current_label))

        i = j # Skip past all merged items

    # Stage 3: Final check for uniqueness
    processed_results = []
    seen_entities = set()

    for word, label in final_merged_results:
        entity_tuple = (word, label)

        if word and entity_tuple not in seen_entities:
            processed_results.append(entity_tuple)
            seen_entities.add(entity_tuple)

    return patient_name, processed_results
