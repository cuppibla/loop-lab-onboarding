"""Fake 'company systems' backed by a JSON file in the current folder.

Survives process restarts (so we can prove durability) and COUNTS side effects
(so we can see the double-order bug and the idempotency fix). Identical across
every level.
"""
import json
import os

STORE = "fake_systems.json"


def _load() -> dict:
    if os.path.exists(STORE):
        with open(STORE) as f:
            return json.load(f)
    return {"accounts": [], "laptop_orders": [], "access_grants": [], "welcomes": []}


def _save(d: dict) -> None:
    with open(STORE, "w") as f:
        json.dump(d, f, indent=2)


def reset() -> None:
    _save({"accounts": [], "laptop_orders": [], "access_grants": [], "welcomes": []})


def create_account(emp: str) -> None:
    d = _load(); d["accounts"].append(emp); _save(d)


def has_laptop_order(emp: str) -> bool:
    return any(o["emp"] == emp for o in _load()["laptop_orders"])


def order_laptop(emp: str) -> str:
    d = _load()
    oid = f"LAP-{len(d['laptop_orders']) + 1}"
    d["laptop_orders"].append({"emp": emp, "order_id": oid})
    _save(d)
    return oid


def grant_access(emp: str, system: str) -> None:
    d = _load(); d["access_grants"].append({"emp": emp, "system": system}); _save(d)


def welcome(emp: str) -> None:
    d = _load(); d["welcomes"].append(emp); _save(d)


def laptop_count(emp: str) -> int:
    return len([o for o in _load()["laptop_orders"] if o["emp"] == emp])


def summary() -> dict:
    d = _load()
    return {k: len(v) for k, v in d.items()}
