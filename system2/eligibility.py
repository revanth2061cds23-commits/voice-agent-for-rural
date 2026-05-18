from __future__ import annotations

from typing import Any


def _get_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "1"}:
            return True
        if v in {"false", "no", "0"}:
            return False
    return None


def _get_land_acres(citizen_profile: dict) -> float | None:
    docs = citizen_profile.get("documents") or {}
    land = docs.get("land_acres", None)
    if land is None:
        land = citizen_profile.get("land_acres", None)
    try:
        return None if land is None else float(land)
    except (TypeError, ValueError):
        return None


def _has_document(citizen_profile: dict, doc_key: str) -> bool:
    docs = citizen_profile.get("documents") or {}
    val = docs.get(doc_key)
    return bool(val)


def _is_bpl(citizen_profile: dict) -> bool:
    docs = citizen_profile.get("documents") or {}
    return bool(docs.get("bpl_card"))


def check_eligibility(citizen_profile: dict, scheme: dict) -> bool:
    """
    Returns True if citizen_profile satisfies scheme eligibility and has
    all required documents present in citizen_profile["documents"].
    """
    elig = scheme.get("eligibility") or {}

    occupation_allowed = elig.get("occupation") or []
    citizen_occupation = (citizen_profile.get("occupation") or "").strip()
    if occupation_allowed:
        occ_set = {str(o).strip() for o in occupation_allowed}
        if "any" not in {o.lower() for o in occ_set} and citizen_occupation not in occ_set:
            return False

    # OR logic for some schemes: income_max OR bpl_required
    income_max = elig.get("income_max", None)
    try:
        citizen_income = citizen_profile.get("income_annual", None)
        citizen_income = None if citizen_income is None else int(citizen_income)
    except (TypeError, ValueError):
        citizen_income = None

    bpl_required = _get_bool(elig.get("bpl_required", None))
    if income_max is not None or bpl_required is not None:
        meets_income = True
        if income_max is not None:
            if citizen_income is None:
                meets_income = False
            else:
                meets_income = citizen_income <= int(income_max)

        is_bpl = _is_bpl(citizen_profile)

        if bpl_required is True and income_max is not None:
            # OR rule: income_max OR BPL
            if not (meets_income or is_bpl):
                return False
        elif bpl_required is True and income_max is None:
            if not is_bpl:
                return False
        elif income_max is not None and bpl_required is not True:
            if not meets_income:
                return False

    land_min_acres = elig.get("land_min_acres", None)
    if land_min_acres is not None:
        citizen_land = _get_land_acres(citizen_profile)
        if citizen_land is None or citizen_land < float(land_min_acres):
            return False

    has_pucca_req = _get_bool(elig.get("has_pucca_house", None))
    if has_pucca_req is not None:
        citizen_has_pucca = _get_bool(citizen_profile.get("has_pucca_house", None))
        if citizen_has_pucca is None or citizen_has_pucca != has_pucca_req:
            return False

    has_lpg_req = _get_bool(elig.get("has_lpg_connection", None))
    if has_lpg_req is not None:
        citizen_has_lpg = _get_bool(citizen_profile.get("has_lpg_connection", None))
        if citizen_has_lpg is None or citizen_has_lpg != has_lpg_req:
            return False

    daughter_req = _get_bool(elig.get("has_daughter_below_10", None))
    if daughter_req is not None:
        citizen_has_daughter = _get_bool(citizen_profile.get("has_daughter_below_10", None))
        if citizen_has_daughter is None or citizen_has_daughter != daughter_req:
            return False

    for doc in scheme.get("required_documents") or []:
        if not _has_document(citizen_profile, doc):
            return False

    return True

