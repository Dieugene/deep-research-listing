"""
Display labels for API responses.
Maps internal codes to human-readable strings used in all API output.
"""

INSTRUMENT_CLASS_LABELS: dict[str, str] = {
    "equity": "Акции",
    "bond": "Облигации",
    "fund": "Фонды",
    "depositary_receipt": "Депозитарные расписки",
}

VENUE_TYPE_LABELS: dict[str, str] = {
    "regulated_market": "Regulated Market",
    "MTF": "MTF",
    "OTF": "OTF",
    "mtf": "MTF",
    "otf": "OTF",
    "exchange_regulated": "Exchange-Regulated",
}

LIFECYCLE_PHASE_LABELS: dict[str, str] = {
    "admission": "Допуск",
    "continuing": "Поддержание",
    "maintenance": "Поддержание",
    "suspension": "Приостановка",
    "delisting": "Исключение",
    "multiple": "Общие требования",
}

CONTENT_TYPE_LABELS: dict[str, str] = {
    "requirements": "Требования",
    "procedures": "Процедуры",
    "monitoring": "Мониторинг и надзор",
    "sanctions": "Санкции",
    "disclosure": "Раскрытие информации",
}

VALIDATION_STATUS_LABELS: dict[str, str] = {
    "green": "Данные верифицированы",
    "yellow": "Требует проверки источников",
    "red": "Данные ненадёжны",
    "unknown": "Статус неизвестен",
}

PARAMETER_STATUS_LABELS: dict[str, str] = {
    "found": "Найден",
    "not_found": "Не найден",
    "not_applicable": "Не применимо",
}

# Section labels for 3A/3B/3C raw content keys → Russian display names
SECTION_LABELS: dict[str, str] = {
    "admission_overview": "Общий обзор допуска",
    "eligibility_requirements": "Требования к эмитенту",
    "instrument_requirements": "Требования к инструменту",
    "procedure_and_timeline": "Процедура и сроки",
    "disclosure_at_admission": "Раскрытие информации при допуске",
    "secondary_admission": "Вторичный допуск",
    "special_regimes": "Специальные режимы",
    "restrictions_and_lock_ups": "Ограничения и lock-up",
    "sponsor_and_infrastructure": "Спонсор и инфраструктура",
    "common_requirements_common": "Общие требования",
    "additional_findings": "Дополнительные сведения",
}
