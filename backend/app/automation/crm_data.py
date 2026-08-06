"""CRM contact loading from Assets CSV + knowledge context."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List


def _candidate_crm_paths() -> List[Path]:
    root = Path(__file__).resolve().parents[3]  # Jarvis/
    return [
        root
        / "Assets"
        / "extracted"
        / "blueprince12-attachments (4)"
        / "07_CRM_Database_759_Targets.csv",
        root / "Assets" / "07_CRM_Database_759_Targets.csv",
    ]


def load_crm_contacts(limit: int = 40) -> List[Dict[str, Any]]:
    for path in _candidate_crm_paths():
        if not path.exists():
            continue
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                email = (row.get("Email") or "").strip()
                company = (row.get("Company") or "").strip()
                if not company:
                    continue
                rows.append(
                    {
                        "company": company,
                        "contact_person": (row.get("Contact_Person") or "").strip(),
                        "title": (row.get("Title") or "").strip(),
                        "email": email,
                        "phone": (row.get("Phone") or "").strip(),
                        "city": (row.get("City") or "").strip(),
                        "country": (row.get("Country") or "").strip(),
                        "region": (row.get("Region") or "").strip(),
                        "type": (row.get("Type") or "").strip(),
                        "priority": (row.get("Priority") or "").strip(),
                        "status": (row.get("Status") or "").strip(),
                        "intel": (row.get("Intel") or "").strip(),
                        "angle": (row.get("Angle") or "").strip(),
                        "next_action": (row.get("Next_Action") or "").strip(),
                    }
                )
                if len(rows) >= limit:
                    break
        return rows
    return []


def contacts_as_text(contacts: List[Dict[str, Any]], limit: int = 25) -> str:
    if not contacts:
        return "No CRM contacts loaded."
    lines = []
    for i, c in enumerate(contacts[:limit], start=1):
        lines.append(
            f"{i}. {c.get('company')} | {c.get('contact_person')} | "
            f"{c.get('email') or 'NO_EMAIL'} | Priority={c.get('priority')} | "
            f"Type={c.get('type')} | Angle={c.get('angle')}"
        )
    return "\n".join(lines)
