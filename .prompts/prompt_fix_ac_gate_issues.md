# Задача: Исправить 3 проблемы ac-gate + перенести скилл в локальную папку

## Контекст
Скилл ac-gate (Anti-Conflict Gate Validator) был создан и прошёл верификацию. Обнаружено 2 MINOR проблемы и 1 INFO, которые нужно исправить. Также скилл нужно перенести из глобальной папки в локальную проекта.

---

## Задача 1: Добавить недостающие параметры в config.yaml

В `config.yaml` отсутствуют 6 параметров, которые ac-gate ожидает. Добавь их:

### 1A. Новая секция `structural` (добавить ПЕРЕД секцией `discourse`)

```yaml
# ─── Structural stage settings ─────────────────────────────────────────────
structural:
  em_dash_ru_max_per_paragraph: 3       # AC-1: max excess (non-copular) em dashes per paragraph in Russian
```

### 1B. Расширить секцию `discourse` (ЗАМЕНИТЬ существующую)

БЫЛО:
```yaml
discourse:
  # Russian academic text has high passive voice rate (domain norm)
  academic_ru_passive_threshold: 0.70   # Flag passive > 70% (vs 20% for English)
```

СТАЛО:
```yaml
discourse:
  # Passive voice thresholds by language+register (AC-4)
  default_passive_threshold: 0.20               # English (any register)
  academic_ru_passive_threshold: 0.70            # Russian academic — domain norm is 50%+
  academic_essay_ru_passive_threshold: 0.50      # Russian academic-essay — intermediate
  journalistic_ru_passive_threshold: 0.30        # Russian journalistic — moderate tolerance
```

### 1C. Добавить 2 ключа в секцию `scoring` (после `p7_context_violations_target: 0`)

```yaml
  # Russian-specific scoring gates (AC-12, AC-15)
  skip_perplexity_for_russian: true              # AC-15: GPT-2 is English-only; skip for ru
  ru_no_odnako_ratio_target: 2.0                 # AC-12: mirrors p29_russian.target_no_odnako_ratio
```

---

## Задача 2: Обновить CLAUDE.md — 2 правки

### 2A. AC-4: Добавить промежуточные пороги

В секции `**AC-4 — Passive Voice Threshold for Russian Academic (HIGH)**` ЗАМЕНИТЬ:

БЫЛО (2 строки):
```
- `language='ru'` AND `register='academic'`: passive threshold = 0.70 (from `config.yaml: discourse.academic_ru_passive_threshold`)
- English or non-academic: passive threshold = 0.20
```

СТАЛО (4 строки):
```
- `language='ru'` AND `register='academic'`: passive threshold = 0.70 (from `config.yaml: discourse.academic_ru_passive_threshold`)
- `language='ru'` AND `register='academic-essay'`: passive threshold = 0.50 (from `config.yaml: discourse.academic_essay_ru_passive_threshold`)
- `language='ru'` AND `register='journalistic'`: passive threshold = 0.30 (from `config.yaml: discourse.journalistic_ru_passive_threshold`)
- English or other combinations: passive threshold = 0.20 (from `config.yaml: discourse.default_passive_threshold`)
```

### 2B. P32 Russian: Добавить 2 модальных глагола

В секции `#### Russian P32 (Modal Hedging on Results)` ЗАМЕНИТЬ:

БЫЛО:
```
Modal hedging ban on result sentences applies identically in Russian. Russian modal verbs: может, мог бы, вероятно, по-видимому, по всей видимости — all banned from sentences containing numerical data.
```

СТАЛО:
```
Modal hedging ban on result sentences applies identically in Russian. Russian modal verbs: может, мог бы, вероятно, по-видимому, по всей видимости, можно предположить, предположительно — all banned from sentences containing numerical data.
```

---

## Задача 3: Перенести ac-gate из глобальной в локальную папку

### 3A. Скопировать всё содержимое из глобальной папки в локальную:

```
ОТКУДА: C:\Users\GamePC\.claude\skills\ac-gate\
КУДА:   skills/ac-gate/   (относительно корня проекта)
```

Структура должна быть:
```
skills/ac-gate/
├── SKILL.md
└── reference/
    ├── ac_rules_full.md
    ├── russian_adaptation_rules.md
    ├── stage_ac_matrix.md
    └── violation_patterns.md
```

### 3B. Обновить `stage_ac_matrix.md` в ЛОКАЛЬНОЙ копии

В таблице `config.yaml` в конце файла ЗАМЕНИТЬ все 4 строки с ❌ MISSING:

БЫЛО:
```
| `structural.em_dash_ru_max_per_paragraph: 3` | AC-1 | ❌ MISSING |
| `scoring.skip_perplexity_for_russian: true` | AC-15 | ❌ MISSING |
| `scoring.ru_no_odnako_ratio_target: 2.0` | AC-12 | ❌ MISSING |
| `discourse.default_passive_threshold: 0.20` | AC-4 | ❌ MISSING (implied but not explicit) |
```

СТАЛО:
```
| `structural.em_dash_ru_max_per_paragraph: 3` | AC-1 | ✅ exists |
| `scoring.skip_perplexity_for_russian: true` | AC-15 | ✅ exists |
| `scoring.ru_no_odnako_ratio_target: 2.0` | AC-12 | ✅ exists |
| `discourse.default_passive_threshold: 0.20` | AC-4 | ✅ exists |
| `discourse.academic_essay_ru_passive_threshold: 0.50` | AC-4 | ✅ exists |
| `discourse.journalistic_ru_passive_threshold: 0.30` | AC-4 | ✅ exists |
```

### 3C. Удалить глобальную копию

После успешного копирования удали папку `C:\Users\GamePC\.claude\skills\ac-gate\` целиком.

---

## Верификация

После всех изменений проверь:

1. `grep "em_dash_ru_max_per_paragraph" config.yaml` → должен найти строку
2. `grep "default_passive_threshold" config.yaml` → должен найти 0.20
3. `grep "academic_essay_ru_passive_threshold" config.yaml` → должен найти 0.50
4. `grep "journalistic_ru_passive_threshold" config.yaml` → должен найти 0.30
5. `grep "skip_perplexity_for_russian" config.yaml` → должен найти true
6. `grep "ru_no_odnako_ratio_target" config.yaml` → должен найти 2.0
7. `grep "можно предположить" CLAUDE.md` → должен найти строку
8. `ls skills/ac-gate/reference/` → 4 файла
9. `grep "MISSING" skills/ac-gate/reference/stage_ac_matrix.md` → 0 совпадений
10. Глобальная папка `C:\Users\GamePC\.claude\skills\ac-gate\` удалена

---

## ВАЖНО: Не менять ничего другого

Все правки строго ограничены перечисленными выше. Не трогай:
- Содержимое SKILL.md
- Содержимое ac_rules_full.md, russian_adaptation_rules.md, violation_patterns.md (кроме stage_ac_matrix.md)
- Другие секции config.yaml и CLAUDE.md
