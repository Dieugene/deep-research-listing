# Task 020: Implementation Report

## Изменённые / созданные файлы

| Действие | Файл |
|----------|------|
| ИЗМЕНЁН | `02_src/pipeline/source_classifier.py` |
| ИЗМЕНЁН | `02_src/run_pipeline.py` |
| СОЗДАН  | `02_src/tools/run_l3_citation_types_catchup.py` |
| СОЗДАН  | `02_src/tools/run_l3_title_fix_catchup.py` |

---

## Новые функции в `02_src/pipeline/source_classifier.py`

### Вспомогательная (приватная)

```python
def _iter_l3_raw_files(jurisdictions: Optional[list[str]]) -> Iterator[tuple[Path, str]]
```
Генератор: обходит все `3A/3B/3C_raw.json` в `COUNTRIES_DIR`. Поддерживает оба варианта хранения — Phase 1 (per-cell subdirectories) и Phase 2 (`_parallel_raw/`). Фильтрует по `jurisdictions` (список `name_ru`), `None` = все.

Возвращает `(raw_path: Path, label: str)` — label используется в логах.

---

### `process_l3_citation_types(jurisdictions=None)`

```python
def process_l3_citation_types(jurisdictions: Optional[list[str]] = None) -> None
```

Добавляет поле `type` ко всем объектам в `citations[]` в каждом `3A/3B/3C_raw.json`.

- Тип определяется через `classify_source_url(url)` (уже существующая функция).
- Идемпотентна: пропускает citations, у которых `type` уже есть и не пустой.
- Атомарная запись через `tempfile.mkstemp + os.replace`.
- Логирует `[UPDATED] label — N citations classified` / `[SKIP] label — already typed`.
- В начале и конце логирует счётчики `files_updated` / `files_skipped`.

---

### `fix_fetched_web_page_titles(jurisdictions=None)`

```python
def fix_fetched_web_page_titles(jurisdictions: Optional[list[str]] = None) -> None
```

Для citations, у которых `title.strip().lower() == "fetched web page"`, пытается получить реальный `<title>` страницы по HTTP.

- Использует только стандартную библиотеку: `urllib.request` + `html.parser`.
- `_TitleParser` — внутренний HTMLParser, читает `<title>` или `<meta property="og:title">`.
- `_fetch_title(url, timeout=10)` — выполняет запрос, читает первые 64 КБ HTML, парсит title.
- Если fetch вернул `None` — логирует `WARNING` с URL, citation не изменяется.
- Атомарная запись только если хотя бы одно значение обновлено в файле.
- Идемпотентна: обрабатывает только citations с placeholder-title.

---

## Изменения в `02_src/run_pipeline.py`

В функции `run_level3(venues)` после Step 6 добавлены два шага, прежний Step 7 стал Step 9:

```
Step 6: Add citations            — без изменений
Step 7: Classify L3 citation types  ← НОВЫЙ
Step 8: Fix 'Fetched web page' titles ← НОВЫЙ
Step 9: Build matrix                ← был Step 7
```

Фильтр по юрисдикциям:
```python
jurisdiction_names = list({v.get("name_ru") for v in venues if v.get("name_ru")})
process_l3_citation_types(jurisdiction_names if jurisdiction_names else None)
fix_fetched_web_page_titles(jurisdiction_names if jurisdiction_names else None)
```

---

## Catchup-скрипты

### `02_src/tools/run_l3_citation_types_catchup.py`

Запускает `process_l3_citation_types()` без фильтра — по всему `03_data/countries/`.

```bash
# из корня репозитория:
D:\_workspace\deep-research-listing\venv\Scripts\python.exe 02_src/tools/run_l3_citation_types_catchup.py
```

### `02_src/tools/run_l3_title_fix_catchup.py`

Запускает `fix_fetched_web_page_titles()` без фильтра — по всему `03_data/countries/`.

```bash
# из корня репозитория:
D:\_workspace\deep-research-listing\venv\Scripts\python.exe 02_src/tools/run_l3_title_fix_catchup.py
```

Рекомендуемый порядок первого запуска:
1. Сначала `run_l3_citation_types_catchup.py` — быстрый, только URL-парсинг.
2. Затем `run_l3_title_fix_catchup.py` — медленнее, делает HTTP-запросы.

---

## Acceptance Criteria

- [x] AC-1: `process_l3_citation_types` добавлена, идемпотентна
- [x] AC-2: `run_level3()` вызывает `process_l3_citation_types` (Step 7) с фильтром
- [x] AC-3: `fix_fetched_web_page_titles` добавлена, идемпотентна
- [x] AC-4: `run_level3()` вызывает `fix_fetched_web_page_titles` (Step 8) с фильтром
- [x] AC-5: Catchup `run_l3_citation_types_catchup.py` создан
- [x] AC-6: Catchup `run_l3_title_fix_catchup.py` создан
- [x] AC-7: Логи содержат счётчики обновлённых файлов и citations per file
