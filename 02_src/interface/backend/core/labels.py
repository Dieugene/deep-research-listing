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
    "common_obligations_common": "Общие обязательства",
    "common_monitoring_common": "Общий мониторинг",
    # 3B nested section labels
    "suspension.procedure": "Процедура приостановки",
    "suspension.grounds": "Основания приостановки",
    "suspension.duration_limits": "Сроки приостановки",
    "suspension.disclosure": "Раскрытие при приостановке",
    "continuing_obligations.periodic_reporting": "Периодическая отчётность",
    "continuing_obligations.compliance_confirmation": "Подтверждение соответствия",
    "continuing_obligations.quantitative_thresholds": "Количественные пороги",
    "continuing_obligations.qualitative_obligations": "Качественные обязательства",
    "delisting_compulsory.grace_period": "Льготный период",
    "delisting_compulsory.procedure": "Процедура принудительного исключения",
    "delisting_compulsory.grounds": "Основания принудительного исключения",
    "delisting_compulsory.disclosure": "Раскрытие при исключении",
    "delisting_compulsory.shareholder_protection": "Защита акционеров",
    "delisting_voluntary.procedure": "Процедура добровольного исключения",
    "delisting_voluntary.conditions": "Условия добровольного исключения",
    "delisting_voluntary.shareholder_approval": "Одобрение акционеров",
    "terminology.suspension_local_term": "Местный термин приостановки",
    "terminology.delisting_local_term": "Местный термин исключения",
    "terminology.source": "Источник терминологии",
    # 3C nested section labels
    "sanctions.regulator_sanctions": "Санкции регулятора",
    "sanctions.exchange_sanctions": "Санкции биржи",
    "sanctions.disciplinary_procedure": "Дисциплинарная процедура",
    "sanctions.appeal_mechanism": "Механизм обжалования",
    "sanctions.publication_of_actions": "Публикация санкций",
    "monitoring_regime.issuer_reporting_to_exchange": "Отчётность эмитента перед биржей",
    "monitoring_regime.exchange_surveillance": "Надзор биржи",
    "monitoring_regime.mechanisms": "Механизмы мониторинга",
    "monitoring_regime.regulator_role": "Роль регулятора",
    "monitoring_regime.sponsor_role": "Роль спонсора",
    "monitoring_regime.responsible_body": "Ответственный орган",
    "enforcement_practice.general_approach": "Общий подход к применению",
    "enforcement_practice.recent_examples": "Недавние примеры",
}
