#!/usr/bin/env python3
"""
Supprime les lignes orphelines de Lignes_Document : celles dont la référence
`Document` pointe vers 0 (aucun devis/facture). Résidus de tests (lignes
dupliquées non reliées), inutiles dans la compta.

Idempotent : une re-exécution ne trouve plus rien à supprimer. Ne touche pas
aux lignes reliées à un document.
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


def main():
    lines = get_table("Lignes_Document")
    orphans = [x["id"] for x in lines if not x["fields"].get("Document")]

    print("=" * 60)
    print("🧹 Nettoyage des lignes orphelines (Document=0)")
    print("=" * 60)
    print(f"Total lignes : {len(lines)}, orphelines : {len(orphans)}")

    if not orphans:
        print("Rien à supprimer.")
        return

    for x in lines:
        if x["id"] in orphans:
            f = x["fields"]
            print(f"  - ligne {x['id']}: {f.get('Description')!r} "
                  f"(qté {f.get('Quantite')} x {f.get('Prix_unitaire')} €)")

    apply([["BulkRemoveRecord", "Lignes_Document", orphans]])
    after = get_table("Lignes_Document")
    restants = [x for x in after if not x["fields"].get("Document")]
    print(f"\n✅ {len(orphans)} lignes orphelines supprimées ; "
          f"il en reste {len(restants)} non reliées (devrait être 0).")


if __name__ == "__main__":
    main()