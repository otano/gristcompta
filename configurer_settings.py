#!/usr/bin/env python3
"""
Crée (si besoin) la table Settings et y insère la ligne de coordonnées de
l'émetteur (LabFab) utilisée dans les en-têtes des PDF (devis/factures).

Idempotent : la table est créée uniquement si absente, et une seule ligne de
référence est insérée si la table est vide. Les valeurs par défaut sont ensuite
modifiables directement depuis Grist.
"""

import os
import requests

from setup_grist import SETTINGS_COLUMNS

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

DEFAULTS = {
    "Raison_Sociale": "LabFab — Association 1901",
    "Adresse": "",
    "Ville_CP": "",
    "Email": "",
    "Telephone": "",
    "SIRET": "",
}


def get_tables():
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables", headers=H)
    r.raise_for_status()
    return [t["id"] for t in r.json()["tables"]]


def get_records(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def create_table(table_id, columns):
    r = requests.post(
        f"{BASE_URL}/api/docs/{DOC_ID}/tables",
        headers=H,
        json={"tables": [{"id": table_id, "columns": columns}]},
    )
    r.raise_for_status()


def main():
    print("=" * 60)
    print("⚙️  Configuration des coordonnées de l'émetteur (table Settings)")
    print("=" * 60)

    if "Settings" not in get_tables():
        create_table("Settings", SETTINGS_COLUMNS)
        print("✅ Table Settings créée.")
    else:
        print("ℹ️  Table Settings déjà présente.")

    records = get_records("Settings")
    if records:
        print(f"ℹ️  Coordonnées déjà présentes (id={records[0]['id']}).")
        return

    r = requests.post(
        f"{BASE_URL}/api/docs/{DOC_ID}/tables/Settings/records",
        headers=H,
        json={"records": [{"fields": DEFAULTS}]},
    )
    r.raise_for_status()
    print("✅ Ligne de coordonnées insérée (modifiable dans Grist).")


if __name__ == "__main__":
    main()