#!/usr/bin/env python3
"""
Applique la numérotation automatique sur la colonne Documents.Numero.

Format : DEV-YYYY-NNN pour les devis, FAC-YYYY-NNN pour les factures.
Le rang NNN est calculé par ordre croissant d'id au sein du même type.
"""

import os
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

FORMULA = '''prefix = "DEV" if $Type == "devis" else "FAC"
year = $Date.year if $Date else YEAR(TODAY())
same_type = sorted([r for r in Documents.all if (r.Type or "") == $Type], key=lambda r: r.id)
for i, r in enumerate(same_type, start=1):
    if r.id == $id:
        return "%s-%d-%03d" % (prefix, year, i)
return "%s-%d-%03d" % (prefix, year, len(same_type) + 1)'''


def main():
    updates = {
        "columns": [
            {"id": "Numero", "fields": {"type": "Text", "isFormula": True, "formula": FORMULA}}
        ]
    }
    url = f"{BASE_URL}/api/docs/{DOC_ID}/tables/Documents/columns"
    r = requests.patch(url, headers=H, json=updates)
    r.raise_for_status()
    print("Colonne Numero configurée comme formule de numérotation automatique.")

    # Vérifier la formule appliquée
    r = requests.get(url, headers=H)
    for c in r.json()["columns"]:
        if c["id"] == "Numero":
            print("Formule enregistrée :")
            print(c["fields"].get("formula"))


if __name__ == "__main__":
    main()
