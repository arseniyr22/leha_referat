"""
Example Loader — loads domain-matched human text excerpts for Stage 4 few-shot injection.

Scans the `Examples with human text` directory, extracts text from PDF/DOCX files,
detects language, caches results, and returns a random ~400-word excerpt from an
English-language file matching the requested domain.

On first run: extracts all files → writes .examples_cache/<stem>.txt + index.json.
Subsequent runs: reads from cache, no re-parsing.
If no English file for domain: falls back to related domains.
If nothing found: returns None; pipeline continues without example (graceful degradation).
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Optional

import yaml
from loguru import logger

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_config: dict = {}


def _load_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


# ── Folder → domain mapping ───────────────────────────────────────────────────

FOLDER_TO_DOMAIN: dict[str, str] = {
    "Economics": "economics",
    "IT": "cs",
    "Law": "general",
    "Management": "management",
    "Math": "math",
    "Other": "general",
    "Politics": "social-science",
    "Social Sciense": "social-science",   # note: folder name has typo
    "Social Science": "social-science",   # accept either spelling
}

# If no English file found for the requested domain, try these in order
DOMAIN_FALLBACKS: dict[str, list[str]] = {
    "general":        ["management", "economics"],
    "social-science": ["economics", "general"],
    "humanities":     ["general", "management"],
    "journalistic":   ["general", "economics"],
    "law":            ["general", "management"],
    "cs":             ["economics", "general"],
    "math":           ["cs", "general"],
    "economics":      ["management", "general"],
    "management":     ["economics", "general"],
}

# Common English words used in language detection
_COMMON_EN: frozenset[str] = frozenset([
    "the", "and", "of", "in", "to", "a", "is", "that", "this", "it",
    "are", "was", "were", "for", "with", "as", "by", "an", "be", "at",
    "from", "or", "but", "not", "on", "which", "have", "had", "has",
    "their", "its", "they", "we", "our", "study", "paper", "analysis",
    "data", "results", "model", "approach", "table", "figure", "show",
    "research", "using", "method", "based", "sample", "hypothesis",
])


class ExampleLoader:
    """
    Loads domain-matched human text excerpts from the configured examples directory.
    """

    def __init__(
        self,
        examples_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        cfg = _load_config().get("examples", {})
        self.examples_dir = (
            examples_dir if examples_dir is not None
            else Path(cfg.get("dir", ""))
        )
        self.cache_dir = (
            cache_dir if cache_dir is not None
            else Path(__file__).parent.parent / cfg.get("cache_dir", ".examples_cache")
        )
        self.excerpt_words = int(cfg.get("excerpt_words", 400))
        self.min_english_ratio = float(cfg.get("min_english_ratio", 0.60))
        self._index: Optional[dict[str, list[dict]]] = None

    # ── Text extraction ───────────────────────────────────────────────────────

    def _extract_pdf(self, path: Path) -> str:
        """Extract text from a PDF using pdfminer.six."""
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            return pdfminer_extract(str(path)) or ""
        except Exception as exc:
            logger.debug(f"PDF extraction failed for {path.name}: {exc}")
            return ""

    def _extract_docx(self, path: Path) -> str:
        """Extract text from a DOCX using python-docx."""
        try:
            from docx import Document  # type: ignore
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:
            logger.debug(f"DOCX extraction failed for {path.name}: {exc}")
            return ""

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix in (".docx", ".doc"):
            return self._extract_docx(path)
        return ""

    # ── Language detection ────────────────────────────────────────────────────

    def _is_english(self, text: str) -> bool:
        """
        Heuristic: ≥ min_english_ratio of the first 200 alphabetic tokens are
        ASCII-only AND at least 5 of them hit the common-English-word set.
        """
        words = re.findall(r"[A-Za-z\u0400-\u04FF]+", text[:3000])
        if len(words) < 20:
            return False
        ascii_words = [w for w in words if w.isascii()]
        if len(ascii_words) / len(words) < self.min_english_ratio:
            return False
        en_hits = sum(1 for w in ascii_words if w.lower() in _COMMON_EN)
        return en_hits >= 5

    # ── Excerpt selection ─────────────────────────────────────────────────────

    def _get_excerpt(self, text: str) -> str:
        """
        Return self.excerpt_words words sampled from the middle 40–80% of the
        document body.  This skips the abstract/intro (first 40%) and the
        conclusion/references (last 20%).
        """
        # Remove PDF rendering artifacts (e.g. "(cid:19)" from pdfminer math output)
        text = re.sub(r"\(cid:\d+\)", "", text)
        # Collapse whitespace for cleaner word splitting
        text = re.sub(r"\s+", " ", text).strip()
        words = text.split()
        n = len(words)

        if n <= self.excerpt_words:
            return text

        start_pct, end_pct = 0.40, 0.80
        window_start = int(n * start_pct)
        window_end = int(n * end_pct) - self.excerpt_words
        if window_end <= window_start:
            window_end = window_start + 1

        start = random.randint(window_start, window_end)
        return " ".join(words[start: start + self.excerpt_words])

    # ── Index management ──────────────────────────────────────────────────────

    def _build_index(self) -> dict[str, list[dict]]:
        """
        Scan examples_dir subdirectories, extract text, cache to disk,
        return index: {domain: [{path, cache_txt, is_english, word_count}]}.
        """
        if not self.examples_dir.exists():
            logger.warning(f"ExampleLoader: examples_dir not found: {self.examples_dir}")
            return {}

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        index: dict[str, list[dict]] = {}
        total = 0

        for folder, domain in FOLDER_TO_DOMAIN.items():
            folder_path = self.examples_dir / folder
            if not folder_path.exists():
                continue
            for f in sorted(folder_path.iterdir()):
                if f.suffix.lower() not in (".pdf", ".docx", ".doc"):
                    continue

                cache_file = self.cache_dir / (f.stem[:80] + f.suffix + ".txt")
                if cache_file.exists():
                    txt = cache_file.read_text(encoding="utf-8", errors="ignore")
                else:
                    logger.debug(f"Extracting {f.name}…")
                    txt = self._extract_text(f)
                    cache_file.write_text(txt, encoding="utf-8")

                if not txt.strip():
                    continue

                is_en = self._is_english(txt)
                entry = {
                    "path": str(f),
                    "cache_txt": str(cache_file),
                    "is_english": is_en,
                    "word_count": len(txt.split()),
                    "folder": folder,
                }
                index.setdefault(domain, []).append(entry)
                total += 1

        index_path = self.cache_dir / "index.json"
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        en_count = sum(
            1 for entries in index.values() for e in entries if e["is_english"]
        )
        logger.info(
            f"ExampleLoader: indexed {total} files, {en_count} English → {index_path}"
        )
        return index

    def _load_index(self) -> dict[str, list[dict]]:
        index_path = self.cache_dir / "index.json"
        if index_path.exists():
            try:
                return json.loads(index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning("ExampleLoader: corrupt index.json, rebuilding…")
        return self._build_index()

    def _get_index(self) -> dict[str, list[dict]]:
        if self._index is None:
            self._index = self._load_index()
        return self._index

    # ── Public API ────────────────────────────────────────────────────────────

    def get_example(self, domain: str) -> Optional[str]:
        """
        Return a ~excerpt_words-word human text excerpt for the given domain.
        Tries domain first, then DOMAIN_FALLBACKS.  Returns None if nothing found.
        """
        index = self._get_index()
        domains_to_try = [domain] + DOMAIN_FALLBACKS.get(domain, [])

        candidates: list[dict] = []
        for d in domains_to_try:
            candidates = [e for e in index.get(d, []) if e["is_english"]]
            if candidates:
                break

        if not candidates:
            logger.debug(f"ExampleLoader: no English example found for domain={domain}")
            return None

        entry = random.choice(candidates)
        txt = Path(entry["cache_txt"]).read_text(encoding="utf-8", errors="ignore")
        excerpt = self._get_excerpt(txt)
        logger.debug(
            f"ExampleLoader: returning {len(excerpt.split())}-word excerpt "
            f"from {Path(entry['path']).name} (domain={domain})"
        )
        return excerpt

    def rebuild_cache(self) -> None:
        """Force-rebuild the extraction cache (call after adding new files)."""
        index_path = self.cache_dir / "index.json"
        if index_path.exists():
            index_path.unlink()
        self._index = None
        self._build_index()
