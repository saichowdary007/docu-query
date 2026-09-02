from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency
    import spacy
except Exception:  # pragma: no cover - dependency not available
    spacy = None


class NER:
    """
    Performs Named Entity Recognition (NER) on text using a spaCy model.
    """

    def __init__(self):
        """Load the spaCy model if the dependency is available."""

        if spacy is None:
            self.nlp = None
        else:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:  # pragma: no cover - model not installed
                self.nlp = None

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts named entities from the given text.

        Args:
            text: The input text string.

        Returns:
            A list of dictionaries, where each dictionary represents an extracted entity
            with its text, start and end characters, and label.
        """
        if self.nlp is None:
            return []
        # In a real async scenario, this might use a non-blocking model or run in a thread pool
        doc = self.nlp(text)
        entities: List[Dict[str, Any]] = []
        for ent in doc.ents:
            entities.append(
                {
                    "text": ent.text,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                    "label": ent.label_,
                }
            )
        return entities
