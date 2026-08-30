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
    "IBAN": "FR76 4255 9000 6941 0200 4522 289",
    "BIC": "CCOPFRPPXXX",
}


def apply(actions):
    """Envoie des actions vers /apply (UpdateRecord, etc.)."""
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    r.raise_for_status()
    return r.json()


def get_tables():
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables", headers=H)
    r.raise_for_status()
    return [t["id"] for t in r.json()["tables"]]


def get_columns(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/columns", headers=H)
    r.raise_for_status()
    return [c["id"] for c in r.json()["columns"]]


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

    # Colonnes manquantes (ex. IBAN/BIC ajoutées après coup)
    existing_cols = set(get_columns("Settings"))
    missing = [c for c in SETTINGS_COLUMNS if c["id"] not in existing_cols]
    if missing:
        r = requests.post(
            f"{BASE_URL}/api/docs/{DOC_ID}/tables/Settings/columns",
            headers=H,
            json={"columns": missing},
        )
        r.raise_for_status()
        print(f"✅ Colonne(s) ajoutée(s) à Settings : {[c['id'] for c in missing]}")

    records = get_records("Settings")
    if not records:
        r = requests.post(
            f"{BASE_URL}/api/docs/{DOC_ID}/tables/Settings/records",
            headers=H,
            json={"records": [{"fields": DEFAULTS}]},
        )
        r.raise_for_status()
        print("✅ Ligne de coordonnées insérée (modifiable dans Grist).")
        return

    # Remplit uniquement les champs encore vides (ne touche pas aux saisies).
    row_id = records[0]["id"]
    fields = records[0]["fields"]
    updates = {k: v for k, v in DEFAULTS.items()
               if (k == "IBAN" or k == "BIC") and not fields.get(k)}
    if updates:
        apply([["UpdateRecord", "Settings", row_id, updates]])
        print(f"✅ Champs complétés : {', '.join(updates)}")
    else:
        print("ℹ️  Coordonnées déjà présentes (id={}).".format(row_id))


if __name__ == "__main__":
    main()