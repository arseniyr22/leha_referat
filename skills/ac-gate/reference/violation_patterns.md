# AC Violation Patterns

Concrete regex patterns and code stubs for detecting AC violations.
Use in BUILD checks (code review) and RUNTIME checks (text analysis).

---

## AC-1 — Em Dash Violations

### RUNTIME: Detect grammatically required Russian em dashes

```python
import re

# Copular em dash: Noun — Noun/Adjective (required by Russian grammar)
COPULAR_DASH_RU = re.compile(
    r'[А-ЯЁа-яё]{3,}\s+—\s+[а-яё]',  # "Москва — столица"
)
# Definition em dash: X — это Y
DEFINITION_DASH_RU = re.compile(r'\b\w+\s+—\s+это\s')

# Em dash count in English text (any = violation)
EM_DASH = re.compile(r'—')


def check_ac1(text: str, language: str) -> dict:
    if language == 'en':
        count = len(EM_DASH.findall(text))
        return {
            'status': 'FAIL' if count > 0 else 'PASS',
            'count': count,
            'fix': 'Replace all em dashes with comma, period, or restructured sentence'
        }

    # Russian: distinguish required vs AI-overuse
    paragraphs = text.split('\n\n')
    violations = []
    total = 0
    required = 0
    for i, para in enumerate(paragraphs):
        dashes = len(EM_DASH.findall(para))
        total += dashes
        req = len(COPULAR_DASH_RU.findall(para)) + len(DEFINITION_DASH_RU.findall(para))
        required += req
        overuse = dashes - req
        if overuse > 3:
            violations.append(f'Para {i+1}: {dashes} dashes ({req} required, {overuse} excess)')
    if required == 0 and total == 0:
        # No copular constructions detected — likely non-issue or short text
        return {'status': 'PASS', 'note': 'No copular constructions found'}
    return {
        'status': 'WARN' if violations else 'PASS',
        'em_dashes_total': total,
        'grammatically_required': required,
        'violations': violations
    }
```

### BUILD: Missing language gate (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — no language gate, removes Russian copular dashes:
def rewrite_text(self, text: str, language: str, register: str) -> str:
    text = self.reduce_em_dashes(text)  # FAIL: destroys "Москва — столица России"
    return text

# ✅ CORRECT — language gate present:
def rewrite_text(self, text: str, language: str, register: str) -> str:
    if language == 'en':
        text = self.reduce_em_dashes(text)       # target: 0
    elif language == 'ru':
        text = self.reduce_em_dashes_ru(text)    # conservative: >3/para only
    return text
```

---

## AC-2 — Citation Format Violations

### RUNTIME: Detect author-year in Russian academic text

```python
import re

# Author-year patterns (FAIL in Russian academic)
AUTHOR_YEAR_RU = re.compile(r'[А-ЯЁ][а-яё]+\s*\(\d{4}\)')  # "Петров (2019)"
AUTHOR_YEAR_EN = re.compile(r'[A-Z][a-z]+\s*\(\d{4}\)')     # "Petrov (2019)"
GOST_CITATION = re.compile(r'\[\d+\]')                        # "[4]"
AUTHOR_WITH_GOST = re.compile(r'[А-ЯЁ][а-яё]+\s*\[\d+\]')  # "Петров [4]" (CORRECT)


def check_ac2(text: str, language: str, register: str) -> dict:
    if language == 'ru' and register == 'academic':
        ay_ru = AUTHOR_YEAR_RU.findall(text)
        ay_en = AUTHOR_YEAR_EN.findall(text)
        all_ay = ay_ru + ay_en
        gost = GOST_CITATION.findall(text)
        # Author-year format is ALWAYS wrong in RU+academic
        # Even "Петров (2019) [4]" is wrong — the (2019) is redundant
        if all_ay:
            return {
                'status': 'FAIL',
                'author_year_found': all_ay[:5],  # show first 5
                'gost_citations': len(gost),
                'fix': 'Remove "(Year)" from all citations. Use "Автор [N]" format only.'
            }
        return {'status': 'PASS', 'gost_citations': len(gost)}
    return {'status': 'N/A', 'reason': f'language={language}, register={register}'}
```

### BUILD: Missing citation format gate (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — forces author-year regardless of language:
def add_attribution(self, text: str, author: str, year: int, claim: str) -> str:
    return f"{author} ({year}) suggests {claim}"  # FAIL for RU+academic

# ✅ CORRECT — language+register gate:
def add_attribution(
    self, text: str, author: str, year: int,
    citation_n: int, claim: str,
    language: str, register: str
) -> str:
    if language == 'ru' and register == 'academic':
        return f"Как утверждает {author} [{citation_n}], {claim}"
    else:
        return f"{author} ({year}) suggests {claim}"
```

---

## AC-3 — GOST Section Order Violations

### RUNTIME: Verify GOST section order is preserved

```python
import re

GOST_SECTIONS_RU = [
    'введение', 'глава 1', 'глава 2', 'глава 3', 'глава 4',
    'заключение',
    'список литературы', 'список использованных источников',
    'приложение',
]
GOST_SECTIONS_EN = [
    'introduction', 'chapter 1', 'chapter 2', 'chapter 3', 'chapter 4',
    'conclusion', 'references', 'bibliography', 'appendix',
]


def check_ac3(text: str, language: str, register: str) -> dict:
    if register != 'academic':
        return {'status': 'N/A'}

    order = GOST_SECTIONS_RU if language == 'ru' else GOST_SECTIONS_EN
    text_lower = text.lower()

    found = []
    for section in order:
        pos = text_lower.find(section)
        if pos != -1:
            found.append((section, pos))

    # Check order: positions must be monotonically increasing
    for i in range(len(found) - 1):
        if found[i][1] > found[i + 1][1]:
            return {
                'status': 'FAIL',
                'issue': f'"{found[i][0]}" appears after "{found[i+1][0]}"',
                'found_order': [s[0] for s in found],
                'fix': f'Restore GOST section order per CLAUDE.md AC-3'
            }
    return {
        'status': 'PASS',
        'found_sections': [s[0] for s in found]
    }
```

### BUILD: Missing protected_sections (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — P26 reorders sections without protection:
def apply_idea_order_disruptor(self, text: str, register: str) -> str:
    sections = self._split_into_sections(text)
    random.shuffle(sections)  # FAIL: shuffles Заключение before Глава 1
    return '\n\n'.join(sections)

# ✅ CORRECT — protected_sections list + paragraph-level only for academic:
PROTECTED_SECTIONS_RU = {
    'введение', 'глава 1', 'глава 2', 'глава 3', 'глава 4',
    'заключение', 'список литературы', 'приложение'
}

def apply_idea_order_disruptor(self, text: str, register: str) -> str:
    if register == 'academic':
        # Academic: paragraph-level reordering ONLY within sections
        return self._reorder_paragraphs_within_sections(text)
    else:
        # Non-academic: section-level reordering allowed
        sections = self._split_into_sections(text)
        reordered = self._reorder_non_protected(sections, PROTECTED_SECTIONS_RU)
        return '\n\n'.join(reordered)
```

---

## AC-4 — Passive Voice Threshold Violations

### RUNTIME: Check passive voice percentage

```python
import re

# Regex fallback for Russian passive detection (when spaCy unavailable)
PASSIVE_RU_REFLEXIVE = re.compile(
    r'\b\w+(?:ется|ются|ился|илась|илось|ились|ется|ются)\b'
)
PASSIVE_RU_SHORT_PART = re.compile(
    r'\b(?:был|была|было|были|будет|будут)\s+\w+(?:ен|ена|ено|ены|ан|ана|ано|аны|ят|ит)\b'
)


def check_ac4(text: str, language: str, register: str) -> dict:
    # Determine correct threshold
    if language == 'ru' and register == 'academic':
        threshold = 0.70
    elif language == 'ru' and register == 'academic-essay':
        threshold = 0.50
    else:
        threshold = 0.20

    if language != 'ru':
        # English passive detection — use spaCy or heuristic
        # (simplified regex fallback)
        sentences = re.split(r'[.!?]+', text)
        passive_markers = re.compile(
            r'\b(?:is|are|was|were|been|being)\s+\w+ed\b'
        )
        passive_count = sum(1 for s in sentences if passive_markers.search(s))
        total = max(len([s for s in sentences if len(s.strip()) > 10]), 1)
        pct = passive_count / total
    else:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return {'status': 'N/A'}
        passive_count = sum(
            1 for s in sentences
            if PASSIVE_RU_REFLEXIVE.search(s) or PASSIVE_RU_SHORT_PART.search(s)
        )
        pct = passive_count / len(sentences)

    if pct > threshold:
        return {'status': 'WARN', 'passive_pct': round(pct, 2), 'threshold': threshold,
                'note': 'Passive voice above threshold'}
    elif language == 'ru' and register == 'academic' and pct < 0.40:
        return {'status': 'WARN', 'passive_pct': round(pct, 2),
                'note': 'Russian academic: passive voice <40% — pipeline may have over-converted to active'}
    return {'status': 'PASS', 'passive_pct': round(pct, 2), 'threshold': threshold}
```

### BUILD: Hardcoded threshold (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — hardcoded threshold, no language gate:
def check_passive_voice(self, text: str) -> bool:
    passive_pct = self._compute_passive_pct(text)
    if passive_pct > 0.20:  # FAIL: wrong threshold for Russian academic
        self.flags.append('passive_voice_high')
    return passive_pct

# ✅ CORRECT — threshold from config, language+register gate:
def check_passive_voice(
    self, text: str, language: str, register: str
) -> float:
    if language == 'ru' and register == 'academic':
        threshold = self.config['discourse']['academic_ru_passive_threshold']
    else:
        threshold = self.config['discourse'].get('default_passive_threshold', 0.20)

    passive_pct = self._compute_passive_pct(text, language=language)
    if passive_pct > threshold:
        self.flags.append(f'passive_voice_high ({passive_pct:.0%} > {threshold:.0%})')
    return passive_pct
```

---

## AC-5 — Figurative Language Violations

### RUNTIME: Detect metaphors in Russian academic text

```python
METAPHOR_MARKERS_RU = [
    'подобно', 'словно', 'как будто', 'своего рода',
    'является своеобразным', 'напоминает', 'сродни',
    'можно сравнить с', 'аналогично тому как',
    'метафорически говоря', 'образно выражаясь',
]


def check_ac5(text: str, language: str, register: str, domain: str = '') -> dict:
    # AC-5 only applies to these combinations
    should_be_empty = (
        (language == 'ru' and register == 'academic') or
        domain == 'math'
    )
    if not should_be_empty:
        return {'status': 'N/A'}

    text_lower = text.lower()
    found = [m for m in METAPHOR_MARKERS_RU if m in text_lower]
    reason = 'RU+academic' if language == 'ru' else f'domain={domain}'
    return {
        'status': 'WARN' if found else 'PASS',
        'metaphor_markers_found': found,
        'reason': f'Metaphors should not appear in {reason} text (AC-5)',
        'fix': 'Remove metaphor/analogy injected by Op 8. State mechanism directly.'
    }
```

### BUILD: Missing Op 8 skip gate (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — Op 8 runs without language/domain gate:
def pass_a_transform(self, text: str, register: str) -> str:
    text = self._inject_metaphors(text)  # FAIL: runs for Russian VKR too
    return text

# ✅ CORRECT — Op 8 gates for language + register + domain:
def pass_a_transform(
    self, text: str, language: str, register: str, domain: str
) -> str:
    # Op 8: Figurative language seed (AC-5)
    skip_op8 = (language == 'ru' and register == 'academic') or domain == 'math'
    if not skip_op8:
        text = self._inject_metaphors(text)  # 1-2 per section
    return text
```

---

## AC-6 / AC-14 — Russian P7/P29 Pattern Violations

### RUNTIME: Detect Russian AI patterns

```python
# From config.yaml: p7_russian + p29_russian
P7_RUSSIAN_ABSOLUTE = [
    'следует отметить', 'является ключевым', 'играет важную роль',
    'необходимо подчеркнуть', 'представляется актуальным',
    'в условиях современности', 'на сегодняшний день', 'в наше время',
    'как известно', 'очевидно, что', 'вышесказанное свидетельствует',
    'немаловажно также', 'актуальность темы заключается в том',
    'данная проблема является актуальной',
    'в рамках данной работы', 'подводя итог вышесказанному',
    'таким образом можно заключить',
]
P7_RUSSIAN_IMPORTANCE = [
    'играет важную роль в', 'является ключевым для',
    'имеет принципиальное значение', 'занимает особое место в',
    'заслуживает особого внимания', 'представляет собой важный',
    'является основополагающим',
]
P7_RUSSIAN_ANNOUNCEMENT = [
    'следует отметить, что', 'необходимо отметить, что',
    'важно подчеркнуть, что', 'стоит отметить, что',
    'обратим внимание на то', 'отметим, что',
    'необходимо указать, что', 'хотелось бы отметить',
]
P29_RUSSIAN_BANNED = [
    'во-первых', 'во-вторых', 'в-третьих', 'помимо этого',
    'в дополнение к вышесказанному',
]


def check_ac6_ac14(text: str, language: str) -> dict:
    if language != 'ru':
        return {'status': 'N/A', 'reason': 'English text; Russian P7 not applicable'}

    text_lower = text.lower()
    violations = []

    for phrase in P7_RUSSIAN_ABSOLUTE:
        if phrase in text_lower:
            violations.append(f'P7 absolute: "{phrase}"')

    for phrase in P7_RUSSIAN_IMPORTANCE:
        if phrase in text_lower:
            violations.append(f'P7 importance-framing: "{phrase}"')

    for phrase in P7_RUSSIAN_ANNOUNCEMENT:
        if phrase in text_lower:
            violations.append(f'P7 announcement: "{phrase}"')

    for connector in P29_RUSSIAN_BANNED:
        if connector in text_lower:
            violations.append(f'P29 banned connector: "{connector}"')

    return {
        'status': 'FAIL' if violations else 'PASS',
        'violations': violations,
        'count': len(violations),
        'fix': 'Remove or rephrase each violation. State content directly without framing.'
    }
```

### BUILD: Missing _apply_russian_patterns call (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — only English patterns applied, Russian goes undetected:
def scan_patterns(self, text: str) -> dict:
    violations = []
    for word in self.config['p7']['absolute_ban']:  # English only
        if word.lower() in text.lower():
            violations.append(word)
    return {'violations': violations}

# ✅ CORRECT — language gate routes to Russian patterns:
def scan_patterns(self, text: str, language: str) -> dict:
    violations = []
    if language == 'ru':
        violations = self._apply_russian_patterns(text, self.config)
    else:
        for word in self.config['p7']['absolute_ban']:
            if word.lower() in text.lower():
                violations.append(word)
    return {'violations': violations, 'language': language}

def _apply_russian_patterns(self, text: str, config: dict) -> list:
    violations = []
    text_lower = text.lower()
    for phrase in config['p7_russian']['absolute_ban']:
        if phrase in text_lower:
            violations.append(f'p7_ru_absolute: {phrase}')
    for phrase in config['p7_russian']['importance_framing_ban']:
        if phrase in text_lower:
            violations.append(f'p7_ru_importance: {phrase}')
    for phrase in config['p7_russian']['announcement_ban']:
        if phrase in text_lower:
            violations.append(f'p7_ru_announcement: {phrase}')
    for conn in config['p29_russian']['absolute_ban']:
        if conn in text_lower:
            violations.append(f'p29_ru_banned: {conn}')
    return violations
```

---

## AC-7 — F5/F6 in Academic Text Violations

### BUILD: Missing F5/F6 skip gate (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — injects F5 (apostrophe drops) into academic text:
def inject_imperfections(self, text: str, language: str) -> str:
    text = self._inject_apostrophe_drops(text, count=4)  # FAIL: injected in VKR
    text = self._inject_grammar_errors(text, count=2)    # FAIL: injected in academic
    return text

# ✅ CORRECT — register + language gates for F5/F6:
def inject_imperfections(
    self, text: str, language: str, register: str
) -> str:
    # F5: apostrophe drops — skip for Russian (inapplicable) and all academic
    skip_f5 = (language == 'ru') or (register == 'academic')
    if not skip_f5:
        text = self._inject_apostrophe_drops(text, count=4)

    # F6: grammar errors — skip for academic (any language)
    skip_f6 = (register == 'academic')
    if language == 'ru' and not skip_f6:
        # Russian journalistic: comma variation only
        text = self._inject_comma_variation(text, count=2)
    elif not skip_f6:
        # English journalistic: subject-verb + comma splice + missing article
        text = self._inject_grammar_errors(text, count=2)

    return text
```

---

## AC-8 — Quote Normalization Violations

### RUNTIME: Detect ASCII quotes in Russian text

```python
import re

ASCII_QUOTE = re.compile(r'"')
GUILLEMETS = re.compile(r'«|»')


def check_ac8(text: str, language: str) -> dict:
    ascii_count = len(ASCII_QUOTE.findall(text))
    guillemet_count = len(GUILLEMETS.findall(text))

    if language == 'ru':
        if ascii_count > 3:
            return {
                'status': 'WARN',
                'ascii_quotes': ascii_count,
                'guillemets': guillemet_count,
                'fix': 'Replace ASCII " with guillemets «» using normalize_quotes_ru()'
            }
        return {'status': 'PASS', 'ascii_quotes': ascii_count, 'guillemets': guillemet_count}

    elif language == 'en':
        if guillemet_count > 0:
            return {
                'status': 'FAIL',
                'guillemets': guillemet_count,
                'fix': 'Replace guillemets «» with ASCII " using normalize_quotes()'
            }
        return {'status': 'PASS'}

    return {'status': 'N/A'}
```

---

## AC-12 — Но:Однако Ratio Check

### RUNTIME: Compute Но:Однако ratio for Russian

```python
import re


def check_ac12(text: str, language: str) -> dict:
    if language == 'ru':
        # Count sentence-initial Но and Однако
        no_pattern = re.compile(r'(?:^|\.\s+)(Но|но)\s', re.MULTILINE)
        odnako_pattern = re.compile(r'(?:^|\.\s+)(Однако|однако)\s', re.MULTILINE)
        no_count = len(no_pattern.findall(text))
        odnako_count = len(odnako_pattern.findall(text))
        ratio = no_count / max(odnako_count, 1)
        return {
            'status': 'PASS' if ratio >= 2.0 else 'WARN',
            'no_odnako_ratio': round(ratio, 2),
            'but_however_ratio': None,  # Not applicable for Russian
            'no_count': no_count,
            'odnako_count': odnako_count,
            'target': 2.0,
            'fix': 'Convert excess "Однако" to "Но" or "Но при этом" at sentence start'
        }
    else:
        # English: But:However ratio
        but_pattern = re.compile(r'(?:^|\.\s+)(But|but)\s', re.MULTILINE)
        however_pattern = re.compile(r'(?:^|\.\s+)(However|however)\s', re.MULTILINE)
        but_count = len(but_pattern.findall(text))
        however_count = len(however_pattern.findall(text))
        ratio = but_count / max(however_count, 1)
        return {
            'status': 'PASS' if ratio >= 2.0 else 'WARN',
            'but_however_ratio': round(ratio, 2),
            'no_odnako_ratio': None,
            'but_count': but_count,
            'however_count': however_count,
            'target': 2.0,
            'fix': 'Convert excess "However" to "But" or "Yet" at sentence start'
        }
```

---

## AC-15 — Perplexity Skip for Russian

### BUILD: Missing perplexity skip gate (VIOLATION vs CORRECT)

```python
# ❌ VIOLATION — computes perplexity for Russian (produces meaningless score):
def compute_perplexity(self, text: str) -> float:
    inputs = self.tokenizer(text, return_tensors='pt')
    loss = self.model(**inputs, labels=inputs['input_ids']).loss
    return torch.exp(loss).item()  # FAIL: GPT-2 can't score Russian

# ✅ CORRECT — language gate skips perplexity for Russian:
def compute_perplexity(self, text: str, language: str) -> float | str:
    if language == 'ru':
        return 'N/A (Russian text)'  # AC-15
    inputs = self.tokenizer(text, return_tensors='pt')
    loss = self.model(**inputs, labels=inputs['input_ids']).loss
    return torch.exp(loss).item()
```

---

## PROMPT Violation Patterns

### Missing {{LANGUAGE}} in Stage 4 prompt (VIOLATION vs CORRECT)

```markdown
❌ VIOLATION — voice_injection.md without language gate:
---
You are a skilled editor. Inject personality, voice, and imperfections
into the text below. Add 1-2 metaphors per section. Apply F5 (3-5
apostrophe drops) and F6 (2-3 grammar errors).
---

✅ CORRECT — voice_injection.md with AC-compliant gates:
---
You are a skilled editor. Language: {{LANGUAGE}}. Register: {{REGISTER}}.
Domain: {{DOMAIN}}.

Inject personality and voice per P30 rules for {{REGISTER}}.

Op 8 (figurative language):
{{#if language == 'ru' and register == 'academic'}}
  SKIP metaphors and analogies entirely. Russian academic text
  uses no figurative language.
{{#else}}
  Add 1-2 metaphors or analogies per section.
{{/if}}

F5/F6 (imperfection texture):
{{#if register == 'academic'}}
  SKIP F5 (apostrophe drops) and F6 (grammar errors) entirely.
  Academic register requires grammatical perfection.
{{#elif language == 'ru'}}
  SKIP F5 (apostrophes don't exist in Russian).
  F6: comma placement variation only (1-2 instances).
{{#else}}
  Apply F5 (3-5 apostrophe drops) and F6 (2-3 minor errors).
{{/if}}
---
```

### Missing {{REGISTER}} in Stage 3 prompt (VIOLATION vs CORRECT)

```markdown
❌ VIOLATION — lexical_enrichment.md converts all citations to author-year:
---
Replace all [N] citation markers with author-year format: "Smith (2019)".
---

✅ CORRECT — language+register gate for citation format:
---
Language: {{LANGUAGE}}. Register: {{REGISTER}}.

Citation format:
{{#if language == 'ru' and register == 'academic'}}
  GOST [N] format ONLY. NEVER convert [N] to author-year.
  Correct: "Как утверждает Иванов [4], ..."
  Incorrect: "Иванов (2019)" ← HARD FAIL
{{#else}}
  Author-year format: "Smith (2019) argues..."
{{/if}}
---
```
