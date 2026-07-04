# data_handler.py
import pandas as pd
import os

# --- Global Glossary Lookup Table ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLOSSARY_FILE = os.path.join(BASE_DIR, 'medical_glossary_large 2.csv')
GLOSSARY_DATA = {}
DEFINITION_NOT_FOUND = "Glossary data not loaded." # Use the original error message for consistency

def load_glossary():
    """Loads the glossary CSV into a global dictionary for fast lookup."""
    global GLOSSARY_DATA

    if not os.path.exists(GLOSSARY_FILE):
        print(f"ERROR: Glossary file not found at {GLOSSARY_FILE}. Definitions will fail.")
        return

    try:
        # Load the CSV
        df = pd.read_csv(GLOSSARY_FILE)

        # Convert to dictionary with normalized keys (all lowercase) for fast, case-insensitive lookup
        # The 'Entity' column is the key, and 'Definition' is the value
        GLOSSARY_DATA = {
            row['Entity'].lower(): row['Definition']
            for index, row in df.iterrows()
        }
        print(f"Successfully loaded {len(GLOSSARY_DATA)} glossary entries.")

    except Exception as e:
        print(f"An error occurred loading the glossary: {e}")
        GLOSSARY_DATA = {} # Ensure it's empty on failure

# Load the glossary immediately when the file is imported
load_glossary()

# --- Lookup Function ---
def get_definition(word: str) -> str:
    """
    Retrieves the simple definition for a given word.

    Args:
        word: The medical entity extracted by the NER model.

    Returns:
        The corresponding definition string, or a failure message.
    """
    # Normalize the word to lowercase for case-insensitive lookup
    normalized_word = word.lower().strip()

    # Check if the word is in the loaded dictionary
    definition = GLOSSARY_DATA.get(normalized_word)

    if definition:
        return definition
    else:
        # If the word is not found, return the expected failure message
        return DEFINITION_NOT_FOUND
