"""Decides whether a job posting is IT-related, using config/it_filter.json."""

import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "it_filter.json"


def _word_pattern(words, flags):
    if not words:
        return None
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    # Whole-word match that also works for keywords starting/ending with symbols (e.g. "ui/ux").
    return re.compile(r"(?<![A-Za-z0-9])(?:" + alternatives + r")(?![A-Za-z0-9])", flags)


class ITFilter:
    def __init__(self, config):
        self.include = _word_pattern(config.get("include", []), re.IGNORECASE)
        self.include_exact = _word_pattern(config.get("include_exact_case", []), 0)
        self.exclude = _word_pattern(config.get("exclude", []), re.IGNORECASE)

    @classmethod
    def load(cls, path=CONFIG_PATH):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def _includes(self, text):
        if not text:
            return False
        return bool(
            (self.include and self.include.search(text))
            or (self.include_exact and self.include_exact.search(text))
        )

    def is_it_job(self, title, categories=()):
        """True when the title (or a category such as job family) looks IT-related
        and the title doesn't look like a sales/finance/HR/etc. role."""
        if self.exclude and title and self.exclude.search(title):
            return False
        return self._includes(title) or any(self._includes(c) for c in categories if c)


class FieldTagger:
    """Tags an IT job with a sub-field such as 'DevOps & Cloud', using the 'fields' list in config/it_filter.json."""

    OTHER = "Other IT"

    def __init__(self, config):
        self.fields = [(f["name"], _word_pattern(f.get("keywords", []), re.IGNORECASE),
                        _word_pattern(f.get("keywords_exact_case", []), 0)) for f in config.get("fields", [])]

    @classmethod
    def load(cls, path=CONFIG_PATH):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    @property
    def names(self):
        return [name for name, _, _ in self.fields] + [self.OTHER]

    def tag(self, title, categories=()):
        for text in [title] + [c for c in categories if c]:
            for name, loose, exact in self.fields:
                if (loose and loose.search(text)) or (exact and exact.search(text)):
                    return name
        return self.OTHER
