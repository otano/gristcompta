#!/usr/bin/env python3
"""
Applique la numérotation automatique sur la colonne Documents.Numero.

Format : DEV-YYYY-NNN pour les devis, FAC-YYYY-NNN pour les factures.
Le numéro est STOCKÉ (colonne de données + trigger « apply to new records ») :
la valeur est calculée au moment de la création comme « plus grand numéro du
même préfixe et de la même année + 1 », puis reste figée — elle survit donc
aux suppressions et aux réutilisations d'id (Grist recycle les id libérés).

Contrairement à une formule recalculée en permanence, ce schéma évite la
référence circulaire (une formule ne peut pas se lire elle-même) : au moment
d'ajouter un enregistrement, le trigger lit les Numero déjà stockés des autres
enregistrements.
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

TRIGGER = '''def _parse(nu):
    try:
        p, y, s = nu.split("-")
        return (p, int(y), int(s))
    except Exception:
        return None

prefix = "DEV" if $Type == "devis" else "FAC"
year = $Date.year if $Date else YEAR(TODAY())
best = None
for r in Documents.all:
    if r.id == $id:
        continue
    v = _parse(r.Numero)
    if v and v[0] == prefix and v[1] == year and (best is None or v[2] > best):
        best = v[2]
return "%s-%d-%03d" % (prefix, year, (best or 0) + 1)'''


def apply(actions):
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    if r.status_code >= 400:
        raise RuntimeError(r.text)
    return r.json()


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def check_column():
    """État de la colonne Numero (type, donnée/formule, trigger)."""
    tables = {r["id"]: r["fields"]["tableId"] for r in get_table("_grist_Tables")}
    for c in get_table("_grist_Tables_column"):
        f = c["fields"]
        if f.get("colId") == "Numero" and tables.get(f.get("parentId")) == "Documents":
            return {
                "isFormula": f.get("isFormula"),
                "recalcWhen": f.get("recalcWhen"),
                "formula": f.get("formula"),
            }
    return None


def main():
    print("=" * 60)
    print("🔢 Numérotation automatique (numéro stocké = max + 1)")
    print("=" * 60)

    # Conversion formule -> données + trigger « apply to new records ».
    # Le changement de colonne recopie les valeurs déjà calculées, puis le
    # trigger ne s'applique qu'aux nouveaux enregistrements (recalcDeps vide,
    # ne pas le passer : liste vide -> AssertionError sandbox).
    apply([["ModifyColumn", "Documents", "Numero", {
        "isFormula": False,
        "formula": TRIGGER,
        "recalcWhen": 0,
    }]])

    col = check_column()
    print(f"Colonne Numero : isFormula={col['isFormula']} recalcWhen={col['recalcWhen']}")

    # Vérifier les numéros stockés des enregistrements existants.
    docs = sorted(get_table("Documents"), key=lambda d: d["id"])
    print("Numéros enregistrés :")
    for d in docs:
        print(f"  doc {d['id']}: {d['fields'].get('Type'):7} {d['fields'].get('Numero')}")

    print("\n✅ Numérotation configurée (max + 1, valeurs stockées, idempotent)")


if __name__ == "__main__":
    main()