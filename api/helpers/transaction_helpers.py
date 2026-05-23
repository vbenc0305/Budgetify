from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from fastapi import HTTPException

from api.transaction_payloads import serialize_transaction_for_api

TransactionDict = Dict[str, Any]

DATE_OUTPUT_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_INPUT_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y",
)
EXPECTED_KEYS = {
    "összeg",
    "tranzakció",
    "tranzakció dátuma",
    "közlemény",
    "típus",
    "bejövő",
    "kimenő",
    "bejövő/kimenő",
    "költési kategória",
}
INPUT_FIELD_ALIASES = {
    "amount": ["Összeg"],
    "date": ["Tranzakció dátuma"],
    "description": ["Közlemény"],
    "tran_type": ["Típus"],
    "for_who": ["Partner neve"],
    "transaction_direction": ["Bejövő/Kimenő"],
    "category": ["Költési kategória"],
}
ROUNDING_KEYWORDS = ["kerek", "felkerek", "kerekites", "kerekítés", "felkerekites"]
JAR_KEYWORDS = [
    "persely",
    "perselybe",
    "perselyből",
    "perselyb",
    "kerek",
    "felkerek",
    "kerekítés",
    "felkerekítés",
    "kerekites",
]
MASS_IMPORT_HEADER_ERROR = (
    "A feltöltött adat listákat tartalmaz, de az első sor nem tűnik fejlécnek. "
    "A mass_import endpoint vagy egy lista objektumokat (List[Dict]) vár, "
    "vagy egy olyan mátrixot ahol az első sor a fejléc "
    "(pl. [['Tranzakció dátuma','Összeg',...], [...], ...]). "
    "Kérlek küldj fejlécet, vagy használd a frontend oldali konverziót."
)


def _normalize_text(value: Any) -> str:
    if not value:
        return ""

    normalized = str(value).lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ö": "o",
        "ő": "o",
        "ú": "u",
        "ü": "u",
        "ű": "u",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return re.sub(r"\s+", " ", normalized).strip()


def _parse_amount(value: Any) -> float:
    if value is None or value == "":
        return 0.0

    cleaned = re.sub(r"[^\d.-]", "", str(value).strip().replace(",", "."))
    if cleaned in {"", ".", "-"}:
        return 0.0

    try:
        parsed = float(cleaned)
    except ValueError:
        match = re.search(r"-?\d+(\.\d+)?", cleaned)
        parsed = float(match.group(0)) if match else 0.0
    return abs(parsed)


def _parse_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime(DATE_OUTPUT_FORMAT)

    raw_value = str(value).strip()
    for date_format in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(raw_value, date_format).strftime(DATE_OUTPUT_FORMAT)
        except ValueError:
            continue

    match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", raw_value)
    if match:
        return match.group(0)
    return raw_value


def _fuzzy_pattern_for_keyword(keyword: str) -> str:
    pattern_body = r"\W*".join(re.escape(character) for character in keyword)
    return r"\b" + pattern_body + r"\b"


def _fuzzy_search_any(text: str, keywords: List[str]) -> Optional[str]:
    for keyword in keywords:
        if re.search(_fuzzy_pattern_for_keyword(keyword), text, flags=re.IGNORECASE):
            return keyword
    return None


def classify_internal_transfer(
    description: str,
    tran_type: str,
    transaction_direction: str,
    for_who: str,
    amount: float,
) -> str:
    """Classify jar/rounding style internal transfers from bank-export fields."""
    del amount  # Signature kept for compatibility with existing callers/tests.

    searchable_text = " ".join(
        [description or "", tran_type or "", transaction_direction or "", for_who or ""]
    )
    normalized_text = _normalize_text(searchable_text)

    if re.search(r"kifiz", normalized_text) or re.search(r"\bkifizet", normalized_text) or re.search(r"kivet", normalized_text):
        return "jar_out"
    if re.search(r"befiz", normalized_text) or re.search(r"\bbefizet", normalized_text):
        return "jar_in"
    if _fuzzy_search_any(normalized_text, ROUNDING_KEYWORDS):
        return "rounding"
    if not _fuzzy_search_any(normalized_text, JAR_KEYWORDS):
        return "none"

    normalized_direction = _normalize_text(transaction_direction)
    normalized_type = _normalize_text(tran_type)
    if "kimen" in normalized_direction or "perselybe" in normalized_type or "atvezetesperselybe" in normalized_type:
        return "jar_in"
    if "bejov" in normalized_direction or "perselybol" in normalized_type or "perselyből" in normalized_type:
        return "jar_out"

    normalized_partner = _normalize_text(for_who)
    if "persely" in normalized_partner:
        return "jar_in"
    if any(keyword in normalized_partner for keyword in ["kifiz", "kivet", "kifizes"]):
        return "jar_out"
    return "none"


def _tx_fingerprint_for_matching(tx: Mapping[str, Any]) -> str:
    """Build a deterministic fingerprint used for duplicate detection."""
    try:
        amount_value = float(tx.get("amount", 0.0) or 0.0)
    except Exception:
        amount_value = 0.0

    return "|".join(
        [
            str(tx.get("date", "")).strip(),
            f"{amount_value:.2f}",
            _normalize_text(tx.get("description", ""))[:200],
            _normalize_text(tx.get("category", "")),
            _normalize_text(tx.get("tran_type", "")),
            _normalize_text(tx.get("internal_transfer", "")),
        ]
    )


def _is_header_row_candidate(row: List[Any]) -> bool:
    if not isinstance(row, list):
        return False
    joined_row = " ".join(str(cell).strip().lower() for cell in row)
    return any(keyword in joined_row for keyword in EXPECTED_KEYS)


def _normalize_input_to_dicts(data: Any) -> List[TransactionDict]:
    """Normalize List[Dict] or matrix-with-header payloads into row dictionaries."""
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="A body-nak listának kell lennie (JSON array).")
    if not data:
        return []
    if isinstance(data[0], dict):
        return data
    if not isinstance(data[0], list):
        raise HTTPException(
            status_code=400,
            detail="A transactions_data formátuma ismeretlen: vár List[Dict] vagy List[List] (fejléc + sorok).",
        )
    if not _is_header_row_candidate(data[0]):
        raise HTTPException(status_code=400, detail=MASS_IMPORT_HEADER_ERROR)

    headers = [str(header).strip() for header in data[0]]
    return [dict(zip(headers, row)) for row in data[1:]]


def _get_row_field(row: Mapping[str, Any], possible_keys: List[str], default: str = "") -> str:
    for key in possible_keys:
        if key in row:
            return str(row.get(key) or default)

    normalized_keys = {candidate.lower() for candidate in possible_keys}
    for key, value in row.items():
        if isinstance(key, str) and key.strip().lower() in normalized_keys:
            return str(value or default)

    return default


def transform_excel_row(row: Mapping[str, Any]) -> TransactionDict:
    """Map an imported bank-export row to the transaction schema used by the API."""
    parsed_amount = _parse_amount(_get_row_field(row, INPUT_FIELD_ALIASES["amount"]))
    parsed_date = _parse_date(_get_row_field(row, INPUT_FIELD_ALIASES["date"]))
    description = _get_row_field(row, INPUT_FIELD_ALIASES["description"])
    tran_type = _get_row_field(row, INPUT_FIELD_ALIASES["tran_type"])
    for_who = _get_row_field(row, INPUT_FIELD_ALIASES["for_who"])
    transaction_direction = _get_row_field(row, INPUT_FIELD_ALIASES["transaction_direction"])
    category = _get_row_field(row, INPUT_FIELD_ALIASES["category"])
    internal_transfer = classify_internal_transfer(
        description,
        tran_type,
        transaction_direction,
        for_who,
        parsed_amount,
    )

    return {
        "amount": parsed_amount,
        "category": category,
        "date": parsed_date,
        "description": description,
        "for_who": for_who,
        "transaction_direction": transaction_direction,
        "tran_type": tran_type,
        "internal_transfer": internal_transfer,
    }


def _serialize_row_field_for_api(value: Any) -> Any:
    if isinstance(value, dict) and any(
        key in value for key in ("for_who", "transaction_direction", "transfer_type", "Transfer type")
    ):
        return serialize_transaction_for_api(value)
    return value


def _serialize_mass_import_response_for_api(payload: Mapping[str, Any]) -> TransactionDict:
    serialized = dict(payload)
    serialized["skipped_duplicates"] = [
        {**item, "row": _serialize_row_field_for_api(item.get("row"))}
        for item in payload.get("skipped_duplicates", [])
    ]
    serialized["errors"] = [
        {**item, "row": _serialize_row_field_for_api(item.get("row"))}
        for item in payload.get("errors", [])
    ]
    return serialized

