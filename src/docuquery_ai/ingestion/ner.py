try:
    import spacy
    SPACY_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency missing
    SPACY_AVAILABLE = False
    spacy = None  # type: ignore
from typing import List, Dict, Any

class NER:
    """Perform simple Named Entity Recognition using spaCy if available."""

    def __init__(self):
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except Exception:
                self.nlp = spacy.blank('en')
        else:  # pragma: no cover - fallback when spaCy is unavailable
            self.nlp = None

    async def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        if self.nlp is None:
            return []
        doc = self.nlp(text)
        return [
            {
                'text': ent.text,
                'start_char': ent.start_char,
                'end_char': ent.end_char,
                'label': ent.label_,
            }
            for ent in doc.ents
        ]
