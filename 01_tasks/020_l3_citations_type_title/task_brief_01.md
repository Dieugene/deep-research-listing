# Task 020: L3 citations — type + title fix

## Что нужно сделать

Два дефекта в citations[] всех `3A_raw.json / 3B_raw.json / 3C_raw.json`:

1. **P2 — Нет поля `type`**: `source_classifier.py` обрабатывает только L1/L2. L3-цитаты не охвачены → все показываются с бейджем «ДРУГОЕ».
2. **P4 — Title «Fetched web page»**: Parallel API не смог получить `<title>` страницы, записал placeholder.

Для каждого дефекта нужны:
- **Pipeline fix** — новый шаг в `run_level3()` (файл `02_src/run_pipeline.py`)
- **Catchup script** — запуск по всему существующему `03_data/countries/`

---

## Зачем

- Все L3 источники отображаются как «ДРУГОЕ» вместо реального типа (rulebook, government и т.д.)
- В панели источников показывается «Fetched web page» вместо названия документа
- При добавлении новых юрисдикций проблемы должны исправляться автоматически, без ручного catchup

---

## Acceptance Criteria

- [ ] AC-1: `process_l3_citation_types(jurisdictions=None)` добавлена в `02_src/pipeline/source_classifier.py`. Сканирует все `3A/3B/3C_raw.json`, добавляет `type` к каждой citation без него. Идемпотентна (пропускает citations с существующим `type`).
- [ ] AC-2: `run_level3()` в `02_src/run_pipeline.py` вызывает `process_l3_citation_types` после шага "Add citations", с фильтром по обрабатываемым юрисдикциям.
- [ ] AC-3: `fix_fetched_web_page_titles(jurisdictions=None)` добавлена в `02_src/pipeline/source_classifier.py`. Сканирует все `3A/3B/3C_raw.json`, для citations где `title == "Fetched web page"` (регистронезависимо) — пытается получить реальный title по URL. Идемпотентна.
- [ ] AC-4: `run_level3()` вызывает `fix_fetched_web_page_titles` после `process_l3_citation_types`, с фильтром по юрисдикциям.
- [ ] AC-5: Catchup-скрипт `02_src/tools/run_l3_citation_types_catchup.py` — запускает AC-1 по всему `03_data/` без фильтра.
- [ ] AC-6: Catchup-скрипт `02_src/tools/run_l3_title_fix_catchup.py` — запускает AC-3 по всему `03_data/` без фильтра.
- [ ] AC-7: В логах виден счётчик обновлённых файлов и citations per file.

---

## Контекст

### Структура L3 citation (текущая)

```json
{
  "url": "https://aquis-public-files.s3.eu-west-2.amazonaws.com/...",
  "title": "AQSE Growth Market – Rules for Issuers",
  "field": "instrument_requirements",
  "excerpts": ["...", "..."]
}
```

Нужно добавить поле `"type": "rulebook"` (или другое значение).

### Структура citation с "Fetched web page" (пример из EQUITY-1 3A)

```json
{
  "url": "https://www.handbook.fca.org.uk/handbook/UKLR/22/",
  "title": "Fetched web page",
  "field": "instrument_requirements",
  "excerpts": []
}
```

### Существующий код в source_classifier.py

Функция `classify_source_url(url)` — уже реализована, возвращает тип по домену URL.
Функция `process_source_types(jurisdictions=None)` — образец для реализации L3 варианта.

Паттерн обхода L3 (из `pipeline/sources.py`, `process_level3_citations()`):
```python
for country_dir in sorted(COUNTRIES_DIR.iterdir()):
    if not country_dir.is_dir(): continue
    l3_root = country_dir / "level_3"
    if not l3_root.exists(): continue
    for venue_dir in sorted(l3_root.iterdir()):
        if not venue_dir.is_dir(): continue
        # Phase 2: _parallel_raw/*.json
        parallel_raw_dir = venue_dir / "_parallel_raw"
        if parallel_raw_dir.exists():
            for raw_path in sorted(parallel_raw_dir.glob("*_raw.json")):
                ...
        # Phase 1: per-cell subdirectories
        cell_dirs = sorted(p for p in venue_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
        for cell_dir in cell_dirs:
            for qt in ["3A", "3B", "3C"]:
                raw_path = cell_dir / f"{qt}_raw.json"
                if raw_path.exists(): ...
```

Фильтр по юрисдикциям: сравнивать `country_dir.name` с `jurisdictions` списком.

### Техника получения HTML title (для fix_fetched_web_page_titles)

Использовать только стандартную библиотеку (без внешних зависимостей):

```python
import urllib.request
from html.parser import HTMLParser

class _TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self.title = None
    def handle_starttag(self, tag, attrs):
        if tag == "title": self._in_title = True
        if tag == "meta":
            attrs_d = dict(attrs)
            if attrs_d.get("property") == "og:title" and self.title is None:
                self.title = attrs_d.get("content", "").strip() or None
    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip() or None
    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False

def _fetch_title(url: str, timeout: int = 10) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(65536).decode("utf-8", errors="replace")
        parser = _TitleParser()
        parser.feed(html)
        return parser.title
    except Exception:
        return None
```

Логика fix:
- `title.strip().lower() == "fetched web page"` → попытаться получить реальный title
- Если `_fetch_title` вернул не None → обновить `citation["title"]`
- Если None → оставить как есть, залогировать warning с URL

### Интеграция в run_pipeline.py

Текущий `run_level3()` (строки 242–291):
```
Step 1: Build prompts
Step 2: Launch Parallel tasks
Step 3: Poll tasks
Step 4: Postprocess
Step 5: Validate
Step 6: Add citations  ← после этого вставить новые шаги
Step 7: Build matrix
```

После правки должно быть:
```
Step 6: Add citations
Step 7: Classify L3 citation types   ← новый
Step 8: Fix 'Fetched web page' titles ← новый
Step 9: Build matrix                  ← был Step 7
```

Для фильтрации по юрисдикциям в `run_level3(venues)`:
```python
jurisdiction_names = list({v.get("name_ru") for v in venues if v.get("name_ru")})
```

### Catchup-скрипты — образец

`02_src/tools/run_source_classifier_catchup.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.source_classifier import process_source_types

if __name__ == "__main__":
    print("Classifying source types...")
    process_source_types()
    print("Done.")
```

### Логи

- Logger создавать через `get_logger("source_classifier", LOGS_DIR / f"source_classifier_{datetime.date.today()}.log")`
- Логгер уже существует в файле — использовать существующий `logger = get_logger(...)` из `source_classifier.py`
- В начале функции логировать `=== L3 citation types: ... ===`
- Per-file: `[UPDATED] cell_id/3A — N citations classified` или `[SKIP] cell_id/3A — already typed`

---

## Файлы для изменения / создания

| Действие | Файл |
|----------|------|
| ИЗМЕНИТЬ | `02_src/pipeline/source_classifier.py` — добавить 2 функции |
| ИЗМЕНИТЬ | `02_src/run_pipeline.py` — добавить шаги 7/8 в run_level3 |
| СОЗДАТЬ | `02_src/tools/run_l3_citation_types_catchup.py` |
| СОЗДАТЬ | `02_src/tools/run_l3_title_fix_catchup.py` |

---

## Важные ограничения

- **Не запускать код**: только писать. Запуск выполняет Tech Lead отдельно.
- **Идемпотентность**: все функции должны безопасно запускаться повторно.
- **Атомарная запись**: использовать `tempfile.mkstemp + os.replace` (паттерн из `_save_json` в `source_classifier.py`).
- **Обработка ошибок**: сетевые ошибки в title fix → log warning, не падать.
- **Существующий logger**: не создавать новый в `source_classifier.py` — использовать тот, что уже есть в начале файла.

---

## Отчёт

После реализации создать `01_tasks/020_l3_citations_type_title/implementation_01.md` с:
- Список изменённых/созданных файлов
- Описание функций (сигнатура + что делает)
- Инструкция запуска catchup-скриптов
