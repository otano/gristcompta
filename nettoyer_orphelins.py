#!/usr/bin/env python3
"""
Supprime les lignes orphelines :
- Lignes_Document : celles dont la référence `Document` pointe vers 0 (aucun
  devis/facture). Résidus de tests (lignes dupliquées non reliées).
- Lignes_Depense : celles dont la référence `Depense` pointe vers 0 (aucune
  dépense parente). Résidus de tests de la refacturation.

Idempotent : une re-exécution ne trouve plus rien à supprimer. Ne touche pas
aux lignes reliées à un document ou à une dépense.
"""

import os
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def apply(actions):
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    if r.status_code >= 400:
        raise RuntimeError(r.text)
    return r.json()


def purge(table, ref_col, ref_label):
    """Supprime les lignes orphelines (ref_col vide) d'une table."""
    lines = get_table(table)
    orphans = [x["id"] for x in lines if not x["fields"].get(ref_col)]
    print(f"  {table} : {len(lines)} lignes, {len(orphans)} orphelines ({ref_col}=0)")
    if not orphans:
        return
    for x in lines:
        if x["id"] in orphans:
            f = x["fields"]
            print(f"    - ligne {x['id']}: {f.get('Description')!r} "
                  f"(qté {f.get('Quantite')} x {f.get('Prix_unitaire')} €)")
    apply([["BulkRemoveRecord", table, orphans]])
    after = get_table(table)
    restants = [x for x in after if not x["fields"].get(ref_col)]
    print(f"  ✅ {len(orphans)} orphelines supprimées ({ref_label}=0) ; "
          f"il en reste {len(restants)} (devrait être 0).")


def main():
    print("=" * 60)
    print("🧹 Nettoyage des lignes orphelines")
    print("=" * 60)
    purge("Lignes_Document", "Document", "Document")
    purge("Lignes_Depense", "Depense", "Depense")
    print("\n✅ Nettoyage terminé")


if __name__ == "__main__":
    main()