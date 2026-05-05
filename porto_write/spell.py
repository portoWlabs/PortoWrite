import os
import logging
from spylls.hunspell import Dictionary
from porto_write.constants import DICTIONARIES_DIR, USER_DICT_FILE

logger = logging.getLogger(__name__)

class SpellChecker:
    """Service for inline spell checking and suggestions using spylls (Hunspell)."""

    def __init__(self):
        self.dict = None
        self.user_words = set()
        self._load_dictionary()
        self._load_user_dictionary()

    def _load_dictionary(self):
        """Load the primary Hunspell dictionary files."""
        aff_path = os.path.join(DICTIONARIES_DIR, "en_US.aff")
        dic_path = os.path.join(DICTIONARIES_DIR, "en_US.dic")
        
        try:
            # spylls expects the .dic and .aff file content or paths
            # According to spylls docs, Dictionary.from_files is a common way
            self.dict = Dictionary.from_files(os.path.join(DICTIONARIES_DIR, "en_US"))
            logger.info("SpellChecker: Primary dictionary (en_US) loaded.")
        except Exception as e:
            logger.error("SpellChecker: Failed to load primary dictionary: %s", e)
            # We don't want to crash the app, but spellcheck won't work
            self.dict = None

    def _load_user_dictionary(self):
        """Load custom words from the user dictionary file."""
        if os.path.exists(USER_DICT_FILE):
            try:
                with open(USER_DICT_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            self.user_words.add(word)
                logger.debug("SpellChecker: Loaded %d user words.", len(self.user_words))
            except Exception as e:
                logger.error("SpellChecker: Failed to load user dictionary: %s", e)

    def check(self, word: str) -> bool:
        """Check if a word is spelled correctly."""
        if not self.dict:
            return True # Fail-safe: assume correct if dict missing
            
        # Clean word (remove surrounding punctuation if any)
        # In a real editor, the tokenizer should handle this, 
        # but we'll do a basic strip here for safety.
        clean_word = word.strip(".,!?;:\"()[]{}")
        if not clean_word:
            return True
            
        # 1. Check user dictionary
        if clean_word in self.user_words:
            return True
            
        # 2. Check main dictionary
        try:
            return self.dict.lookup(clean_word)
        except Exception as e:
            logger.error("SpellChecker: Lookup error for '%s': %s", clean_word, e)
            return True

    def suggest(self, word: str) -> list[str]:
        """Get spelling suggestions for a misspelled word."""
        if not self.dict:
            return []
            
        clean_word = word.strip(".,!?;:\"()[]{}")
        try:
            return list(self.dict.suggest(clean_word))
        except Exception as e:
            logger.error("SpellChecker: Suggestion error for '%s': %s", clean_word, e)
            return []

    def add_to_user_dict(self, word: str):
        """Permanently add a word to the user dictionary."""
        clean_word = word.strip(".,!?;:\"()[]{}")
        if clean_word and clean_word not in self.user_words:
            self.user_words.add(clean_word)
            try:
                # Append to file
                os.makedirs(os.path.dirname(USER_DICT_FILE), exist_ok=True)
                with open(USER_DICT_FILE, "a", encoding="utf-8") as f:
                    f.write(clean_word + "\n")
                logger.info("SpellChecker: Added '%s' to user dictionary.", clean_word)
            except Exception as e:
                logger.error("SpellChecker: Failed to save user word '%s': %s", clean_word, e)
