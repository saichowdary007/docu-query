import spacy
from typing import List, Dict, Any

class NER:
    """
    Performs Named Entity Recognition (NER) on text using a spaCy model.
    """
    def __init__(self):
        """
        Initializes the NER component by loading the 'en_core_web_sm' spaCy model.
        """
        self.nlp = spacy.load('en_core_web_sm')

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts named entities from the given text.

        Args:
            text: The input text string.

        Returns:
            A list of dictionaries, where each dictionary represents an extracted entity
            with its text, start and end characters, and label.
        """
        # In a real async scenario, this might use a non-blocking model or run in a thread pool
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'start_char': ent.start_char,
                'end_char': ent.end_char,
                'label': ent.label_
            })
        return entities
