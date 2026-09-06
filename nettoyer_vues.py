#!/usr/bin/env python3
"""
Supprime les vues/pages inutilisées du document Grist :
- les pages « Clients » et « Membres » (doublons visuels de la table
  Personnes, qui porte une colonne Role : les widgets devis/facture lisent
  Personnes directement et n'ont besoin d'aucune de ces vues) ;
- la vue « projets » en minuscule (reliquat d'une première itération, doublon
  de la page « Projets »).

NB : les sections `parentId=0` (2 par table, record + single) sont les
sections « raw view » protégées de Grist — les retirer est refusé par le
sandbox (« Cannot remove raw view section ») ; elles sont normales et
indispensables, on n'y touche pas.

Ne supprime QUE des vues, jamais de données (les records de Personnes,
Documents… sont intacts).

Idempotent : une re-exécution ne trouve plus rien à supprimer.
"""

import os
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Vues à supprimer, identifiées par leur nom (recherche plutôt que par id :
# les id numériques changent selon l'ordre de création).
VIEWS_TO_REMOVE = ["Clients", "Membres", "projets"]


def apply(actions):
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    if r.status_code >= 400:
        raise RuntimeError(r.text)
    return r.json()


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def find_views_to_remove():
    """Retourne les id des vues nommées à supprimer, classés par nom."""
    found = {}
    for rec in get_table("_grist_Views"):
        name = rec["fields"].get("name")
        if name in VIEWS_TO_REMOVE:
            found.setdefault(name, rec["id"])
    return found


def main():
    print("=" * 60)
    print("🧹 Nettoyage des vues inutilisées")
    print("=" * 60)

    views = find_views_to_remove()
    if views:
        for name, vid in views.items():
            apply([["RemoveView", vid]])
            print(f"✅ Vue '{name}' supprimée (id={vid}).")
    else:
        print("ℹ️  Aucune de ces vues à supprimer (déjà propre) : "
              + ", ".join(VIEWS_TO_REMOVE))

    print("\n✅ Nettoyage terminé (idempotent)")


if __name__ == "__main__":
    main()