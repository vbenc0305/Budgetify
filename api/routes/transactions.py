import math
from tabnanny import verbose

import pandas as pd
from starlette.responses import JSONResponse

from api.dependencies import get_current_user_uid
from db.firebase_client import get_user_transactions, save_user_transaction, save_user_transactions, FirebaseUnavailable
from src.models.transactions import Transaction
from typing import List, Dict, Any, Optional
from fastapi import Body, Depends, HTTPException, APIRouter
import re
import asyncio
from datetime import datetime
import threading
import importlib
import logging

logger = logging.getLogger(__name__)
logger.debug("api.routes.transactions imported")

router = APIRouter()
# Do not initialize pipeline at import time; create lazily on first request
_pipeline_lock = threading.Lock()
_pipeline: Optional[object] = None

EXPECTED_KEYS = {"összeg", "tranzakció", "tranzakció dátuma", "közlemény", "típus", "bejövő", "kimenő", "bejövő/kimenő", "költési kategória"}


def _get_pipeline() -> object:
    """Return a cached ForecastPipeline, creating it in a background thread on first call.
    This performs a lazy import of the Generation module to avoid import-time side-effects.
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _pipeline_lock:
        if _pipeline is not None:
            return _pipeline
        try:
            # lazy import the module that defines ForecastPipeline
            gen_mod = importlib.import_module("src.Generation.Case_one_has_enough_Transact_arima")
            ForecastPipeline = getattr(gen_mod, "ForecastPipeline")
            # create pipeline in thread to avoid blocking asyncio event loop
            _pipeline = asyncio.get_event_loop().run_until_complete(asyncio.to_thread(ForecastPipeline))
            return _pipeline
        except Exception as e:
            logger.exception("Failed to initialize ForecastPipeline")
            raise HTTPException(status_code=500, detail=f"Failed to initialize ForecastPipeline: {e}")

@router.get("/transactions")
async def get_transactions(uid: str = Depends(get_current_user_uid)):
    try:
        transaction_doc = get_user_transactions(uid)
        return transaction_doc or []
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in get_transactions: {e}")
        raise HTTPException(status_code=503, detail=str(e))

# --- PUT egy tranzakcióhoz
@router.put("/transactions")
async def put_transaction(
    transaction_data: dict = Body(...),
    uid: str = Depends(get_current_user_uid)
):
    try:
        # Transaction példány létrehozása a body alapján
        transaction = Transaction(
            amount=transaction_data['amount'],
            category=transaction_data['category'],
            date=transaction_data['date'],
            description=transaction_data.get('description', ''),
            for_who=transaction_data.get('for_who', ''),
            tran_type=transaction_data['tran_type'],
            user_id=uid
        )
        # Mentés Firebase-be
        save_user_transaction(uid, transaction.to_dict())
        return {"status": "success", "transaction": transaction.to_dict()}
    except FirebaseUnavailable as e:
        logger.error(f"Firebase unavailable in put_transaction: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- POST tömeges import (frissített, duplikáció-ellenőrzéssel) ---
@router.post("/transactions/mass_import")
async def mass_import_transactions(
    transactions_data: Any = Body(...),
    uid: str = Depends(get_current_user_uid)
):
    # Normalize input -> List[Dict]
    rows = _normalize_input_to_dicts(transactions_data)

    transactions_to_save = [transform_excel_row(tx) for tx in rows]
    imported_transactions = []
    errors = []           # sikertelen sorok: (index, message)
    skipped_duplicates = []  # duplikáltak (index, reason, row)

    # --- Lekérjük a meglévő tranzakciókat a felhasználótól és előállítjuk a fingerprint set-et ---
    try:
        existing_txs = get_user_transactions(uid) or []
    except Exception as e:
        # ha a get_user_transactions hibázik, logoljuk, de próbáljuk folytatni (később mentésnél lehet gond)
        existing_txs = []
        print(f"⚠️ get_user_transactions hiba (folytatom importot): {e}")

    existing_fps = set()
    for et in existing_txs:
        try:
            existing_fps.add(_tx_fingerprint_for_matching(et))
        except Exception:
            # ignore single problematic existing doc
            continue

    # hasznos a bejövőn belüli ismétlődések elkerülésére
    new_fps = set()

    for idx, tx_data in enumerate(transactions_to_save):
        # debug kiírás (opcionális)
        print(f"[DEBUG] idx={idx}, tx_data={tx_data}")

        try:
            # előállítjuk a fingerprintet (a transform már normalizálta a mezőket: amount, date, ...).
            fp = _tx_fingerprint_for_matching(tx_data)

            # ha már létezik a DB-ben, akkor kihagyjuk
            if fp in existing_fps:
                skipped_duplicates.append({
                    "index": idx,
                    "reason": "already_in_db",
                    "fingerprint": fp,
                    "row": tx_data
                })
                continue

            # ha az importon belül már szerepelt ugyanez, akkor szintén kihagyjuk
            if fp in new_fps:
                skipped_duplicates.append({
                    "index": idx,
                    "reason": "duplicate_in_upload",
                    "fingerprint": fp,
                    "row": tx_data
                })
                continue

            # minden OK -> létrehozzuk a Transaction objektumot és hozzáadjuk mentésre
            tx = Transaction(
                amount=tx_data["amount"],
                category=tx_data["category"],
                date=tx_data["date"],
                description=tx_data["description"],
                for_who=tx_data["for_who"],
                tran_type=tx_data["tran_type"],
                user_id=uid,
                internal_transfer=tx_data.get("internal_transfer", None),
            )
            imported_transactions.append(tx.to_dict())
            new_fps.add(fp)

        except Exception as e:
            errors.append({"index": idx, "error": str(e), "row": tx_data})

    # persistálás: csak a sikereseket mentjük
    if imported_transactions:
        try:
            save_user_transactions(uid, imported_transactions)
        except Exception as e:
            # ha a mentés hibázik, visszajelzünk és nem veszítjük el az információt
            raise HTTPException(status_code=500, detail=f"Mentés sikertelen: {e}")

    # válasz: részletes eredmény (importált, kihagyott duplikátok, hibák)
    return {
        "status": "success" if not errors and not skipped_duplicates else ("partial_success" if imported_transactions else "failed"),
        "imported_count": len(imported_transactions),
        "skipped_duplicates_count": len(skipped_duplicates),
        "skipped_duplicates": skipped_duplicates[:50],  # csak az első 50-et küldjük vissza, hogy ne terheljük a választ
        "failed_count": len(errors),
        "errors": errors,
    }


@router.get("/predict/transactions", response_class=JSONResponse)
async def predict_future_transactions(uid: str = Depends(get_current_user_uid)):
    """
    Lekéri a raw tranzakciókat, átadja a pipeline-nak (tx_list paraméterként),
    és visszaadja a dátummal párosított history/forecast/ci/metrics JSON-t.
    """
    # 1) raw tranzakciók lekérése az adatbázisból (sync hívás feltételezve)
    try:
        tx_list = get_user_transactions(uid) or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {e}")

    # 2) pipeline futtatása háttérszálon, tx_list-tel (így nem duplikáljuk a feature-engineeringet)
    try:
        result = await asyncio.to_thread(_get_pipeline().run, uid=uid, plot=False, verbose=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast pipeline error: {e}")

    def _sanitize_value(v:Any)->Any:
        """Konvertál minden numerikus/Numpy-szerű értéket Python float-ra.
           Nem-finite értékeket (inf, -inf, nan) None-ra cserélünk.
           Rekurzívan kezeli a dict/list/tuple struktúrákat.
        """
        # dict
        if isinstance(v, dict):
            return {k:_sanitize_value(val) for k, val in v.items()}
        if isinstance(v, (list,tuple)):
            return [_sanitize_value(x) for x in v]
        try:
            f = float(v)
        except Exception:
            return v

        if math.isfinite(f):
            return f
        return None

    public_result = {
        "status": result.get("status"),
        "data_source": result.get("data_source"),
        "history": result.get("history"),  # list of {date, value}
        "forecast": result.get("forecast"),  # list of {date, value}
        "ci": result.get("ci"),
        "metrics": result.get("metrics", {}),
    }

    sanitized = _sanitize_value(public_result)

    return JSONResponse(content=sanitized)



# feltételezzük: Transaction osztály importálva van valahonnan
# from .transactions import Transaction
# from .auth import get_current_user_uid
# from .persistence import save_user_transactions

JAR_KEYWORDS = [
    r"persely", r"perselybe", r"perselyből", r"perselyb", r"kerek", r"felkerek",
    r"kerekítés", r"felkerekítés", r"kerekites",
]


def _parse_amount(value: Any) -> float:
    if value is None or value == "":
        return 0.0

    s = str(value).strip()

    # bank exports sometimes use comma as thousands or decimal sep; replace comma with dot
    s = s.replace(",", ".")
    # remove currency labels and anything non-digit except dot and minus
    s_clean = re.sub(r"[^\d\.\-]", "", s)

    if s_clean in ("", ".", "-"):
        return 0.0

    try:
        parsed = float(s_clean)
    except ValueError:
        m = re.search(r"-?\d+(\.\d+)?", s_clean)
        parsed = float(m.group(0)) if m else 0.0
        
    return abs(parsed)


def _parse_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    s = str(value).strip()
    # tried formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    # try to extract an ISO-like timestamp inside the string
    m = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", s)
    if m:
        return m.group(0)
    # fallback: return original string (caller can decide)
    return s


def _normalize_text(s: Any) -> str:
    if not s:
        return ""
    t = str(s).lower()
    # egyszerű diakritikus normalizáció, hogy a kulcsszavak jól találjanak
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ö", "o").replace("ő", "o").replace("ú", "u").replace("ü", "u").replace("ű", "u")
    t = re.sub(r"\s+", " ", t)
    return t


# helper: fuzzy pattern builder
def _fuzzy_pattern_for_keyword(kw: str) -> str:
    """
    Létrehoz egy regex mintát, ami engedi, hogy a kw karakterei között
    tetszőleges nem-alfanumerikus karakter(ek) legyenek (pl. szóköz, pont, vessző).
    Példa: 'persely' -> r'\bp\W*e\W*r\W*s\W*e\W*l\W*y\b'
    """
    # escape a keyword minden karakterét, majd illesszünk közé \W* mintát
    parts = [re.escape(ch) for ch in kw]
    body = r"\W*".join(parts)
    # word boundary a széleken
    return r"\b" + body + r"\b"

def _fuzzy_search_any(s: str, keywords: List[str]) -> str | None:
    """Visszaadja az első keyword-öt, ami fuzzy match-elhető a stringben (vagy None)."""
    for kw in keywords:
        pat = _fuzzy_pattern_for_keyword(kw)
        if re.search(pat, s, flags=re.IGNORECASE):
            return kw
    return None



# új classify függvény
def classify_internal_transfer(description: str, tran_type: str, for_who: str, amount: float) -> str:
    """
    Robosztusabb bedlső-átutalás osztályozás:
      - először explicit kulcsszavakat keresünk (kifiz, befiz, kerek)
      - utána fuzzy keresést futtatunk a JAR_KEYWORDS-en (szóköz/írásjel-tűrés)
      - fallbackként a tran_type alapján döntünk ('income'/'bejövő' -> jar_in, 'outgoing'/'kimenő' -> jar_out)
    """
    # összeállítjuk a vizsgálandó szöveget
    s = " ".join([description or "", tran_type or "", for_who or ""])
    s_norm = _normalize_text(s)

    # 1) Explicit irány meghatározás, ha a leírásban ott van a 'kifiz' vagy 'befiz'
    # (ez lefedi pl. "Kifizetés Tanulmányok perselyből")
    if re.search(r"kifiz", s_norm) or re.search(r"\bkifizet", s_norm) or re.search(r"kivet", s_norm):
        return "jar_out"
    if re.search(r"befiz", s_norm) or re.search(r"\bbefizet", s_norm):
        return "jar_in"

    # 2) Kerekítés-szerű szavak (rounding)
    rounding_kw = ["kerek", "felkerek", "kerekites", "kerekítés", "felkerekites"]
    if _fuzzy_search_any(s_norm, rounding_kw):
        return "rounding"

    # 3) Ha a JAR_KEYWORDS közül bármi fuzzy megtalálható -> döntés a tran_type alapján vagy amount alapján
    #    (de mivel amount-ot abs-zárod, ne alapozz rá; tran_type jobb)
    jar_kw_list = [kw for kw in JAR_KEYWORDS]  # eredeti kulcsszavak
    found = _fuzzy_search_any(s_norm, jar_kw_list)
    if found:
        # tran_type normalizálása (pl. 'Bejövő' -> 'bejovo' stb.)
        tnorm = _normalize_text(tran_type or "")
        if any(k in tnorm for k in ["bejov", "income", "in", "azon", "befiz"]):
            return "jar_in"
        if any(k in tnorm for k in ["kimen", "out", "ki", "kolt"]):
            return "jar_out"
        # ha tran_type nem segít, próbáljuk a 'for_who' mezőt
        fnorm = _normalize_text(for_who or "")
        if any(k in fnorm for k in ["befiz", "bejov", "jar", "persely"]):
            return "jar_in"
        if any(k in fnorm for k in ["kifiz", "kivet", "kifizes"]):
            return "jar_out"
        # végső fallback: ha semmi nincs, jar_out lehet gyakoribb (de te döntesz)
        return "jar_out"

    # 4) se kerek, se jar kulcsszó — fallback tran_type alapján
    tnorm = _normalize_text(tran_type or "")
    if any(k in tnorm for k in ["bejov", "income", "in"]):
        return "jar_in"
    if any(k in tnorm for k in ["kimen", "out", "ki"]):
        return "jar_out"

    # 5) teljes fallback: none (nem belső)
    return "none"


# --- helper: tranzakció fingerprint előállítása ---
def _tx_fingerprint_for_matching(tx: Dict[str, Any]) -> str:
    """
    Egyszerű, determinisztikus fingerprint: date(YYYY-MM-DD), amount(2 dec), normalized description,
    category, tran_type, internal_transfer.
    Ezzel kiszűrhetjük a pontos duplikációkat (és a legtöbb tipikus bank-export duplát).
    """
    # date: csak a nap rész (ha "YYYY-MM-DD HH:MM:SS" formátumú)
    date_raw = str(tx.get("date", "")).strip()
    date_day = date_raw.split(" ")[0] if date_raw else ""
    # amount: szám -> kerekítve 2 tizedesre stringként
    try:
        amount_val = float(tx.get("amount", 0.0) or 0.0)
    except Exception:
        amount_val = 0.0
    amount_s = f"{amount_val:.2f}"
    # normalizált text mezők
    desc = _normalize_text(tx.get("description", ""))[:200]  # rövidítsuk, hogy ne legyen túl hosszú string
    cat = _normalize_text(tx.get("category", ""))
    ttype = _normalize_text(tx.get("tran_type", ""))
    internal = _normalize_text(tx.get("internal_transfer", ""))

    # join: egyértelmű separatorral
    return "|".join([date_day, amount_s, desc, cat, ttype, internal])



# -- helperok a bejövő adatok normalizálásához --

def _is_header_row_candidate(row: List[Any]) -> bool:
    """
    Megpróbáljuk eldönteni, hogy a lista sor fejléc-e.
    Egyszerű heuristics: ha a cellák között van legalább 1-2 olyan, ami tartalmaz
    várt kulcsszavakat (pl. 'Összeg', 'Tranzakció', stb.).
    """
    if not isinstance(row, list):
        return False
    joined = " ".join([str(x).strip().lower() for x in row])
    # ha bármelyik expected key megtalálható a joined stringben -> fejlécnek tekintjük
    return any(k in joined for k in EXPECTED_KEYS)


def _normalize_input_to_dicts(data: Any) -> List[Dict[str, Any]]:
    """
    Átalakít bármilyen bejövő formátumot (List[Dict], List[List-with-header]) -> List[Dict].
    Ha a bejövő adatszerkezet nem egyértelmű, HTTPException-t dob.
    """
    if isinstance(data, list):
        if not data:
            return []
        # 1) Ha már dict-eket kaptunk
        if isinstance(data[0], dict):
            return data  # feltételezzük, hogy minden elem dict
        # 2) Ha listákból áll a mátrix (feltételezve, hogy az első sor a fejlécek)
        if isinstance(data[0], list):
            # ha az első sor bármilyen okból fejlécnek tűnik -> header
            if _is_header_row_candidate(data[0]):
                headers = [str(h).strip() for h in data[0]]
                rows = []
                for r in data[1:]:
                    # Ha sor rövidebb/hosszabb, a zip csak a közös hosszra megy
                    rows.append(dict(zip(headers, r)))
                return rows
            else:
                # első sor nem fejléc: lehet, hogy a kliens nem küldött fejlécet.
                # Nem akarunk vakon feltételezni oszlop-sorrendet (veszélyes),
                # ezért inkább kényelmes, jó hibaüzenetet adunk.
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "A feltöltött adat listákat tartalmaz, de az első sor nem tűnik fejlécnek. "
                        "A mass_import endpoint vagy egy lista objektumokat (List[Dict]) vár, "
                        "vagy egy olyan mátrixot ahol az első sor a fejléc (pl. [['Tranzakció dátuma','Összeg',...], [...], ...]). "
                        "Kérlek küldj fejlécet, vagy használd a frontend oldali konverziót."
                    )
                )
        # 3) egyéb (pl. a listában vegyes típus) -> hibázunk
        raise HTTPException(status_code=400, detail="A transactions_data formátuma ismeretlen: vár List[Dict] vagy List[List] (fejléc + sorok).")
    # nem lista
    raise HTTPException(status_code=400, detail="A body-nak listának kell lennie (JSON array).")


def transform_excel_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Átalakítja a feltöltött Excel sort a Transaction modell által elvárt formátumba,
    és hozzáadja az 'internal_transfer' mezőt is.
    Feltételezi, hogy 'row' egy dict (kulcsok a fejlécek).
    """
    # Kisebb normalizáció: néha a kulcsoknak nincs ékezetük vagy más a név,
    # itt egyszerű megközelítéssel több variánst is ellenőrzünk.
    def get_field(possible_keys, default=""):
        for k in possible_keys:
            if k in row:
                return row.get(k)
        # próbáljuk meg a kisbetűsített kulcsot is
        for k in list(row.keys()):
            if isinstance(k, str) and k.strip().lower() in [pk.lower() for pk in possible_keys]:
                return row.get(k)
        return default

    parsed_amount = _parse_amount(get_field(["Összeg"]))
    parsed_date = _parse_date(get_field(["Tranzakció dátuma"]))
    description = get_field(["Közlemény"])
    tran_type = get_field(["Típus"])
    for_who = get_field(["Bejövő/Kimenő"])
    category = get_field(["Költési kategória"])

    internal = classify_internal_transfer(description, tran_type, for_who, parsed_amount)

    return {
        "amount": parsed_amount,
        "category": category,
        "date": parsed_date,
        "description": description,
        "for_who": for_who,
        "tran_type": tran_type,
        "internal_transfer": internal,
    }
