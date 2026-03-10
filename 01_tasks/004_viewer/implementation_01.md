# Отчет о реализации: Streamlit Viewer (L1+L2+L3)

## Что реализовано

Минимальный файловый просмотрщик данных пайплайна на Streamlit. Три вкладки: «Юрисдикция» (ключевые поля из jurisdiction_card.json), «Площадка» (venue_card.json + таблица тиров), «Ячейки» (таблица статусов L3 + раскрытие raw JSON для готовых результатов). LLM-вызовов нет.

## Файлы

**Новые:**
- `02_src/viewer/__init__.py`
- `02_src/viewer/data_loader.py`
- `02_src/viewer/app.py`

## Особенности реализации

- `cells_list.json` хранит ячейки в обёртке `{"cells": [...]}`, а не как plain list. `load_cells_list()` обрабатывает оба формата.
- `@st.cache_data(ttl=30)` кешируют все файловые чтения на 30 секунд — данные обновляются по мере появления новых L3 результатов без перезапуска viewer.
- При итерации ячеек используется `enumerate` для передачи `cell_index=i` в `get_l3_status` / `load_l3_result` — корректная работа с дублирующимися cell_id (AQSE/HKEX).
- Статус N/A (`—`) показывается когда `prompts[qt] is None`, то есть тип запроса не применим для данной ячейки.
- Streamlit установлен в venv проекта: `venv\Scripts\pip install streamlit`.

## Запуск

```
venv\Scripts\streamlit run 02_src\viewer\app.py
```

## Известные проблемы

Нет
