#!/usr/bin/env python3
"""
Crée les pages/vues du document Grist (Devis, Factures, Refacturation,
Clients, Membres, Projets, Dépenses) avec leurs filtres, via l'API /apply
et la table _grist_Filters.

Stratégie :
- Une "page" Grist = une vue (_grist_Views) + une ou plusieurs sections
  (_grist_Views_section).
- Une nouvelle vue est créée avec l'action  AddView(table_id, view_type, name).
- Un filtre est ajouté avec un enregistrement dans _grist_Filters
  (viewSectionRef, colRef, filter, pinned).

colRefs (extraits de _grist_Tables_column) :
  Documents(tableRef=10): Type=88, Statut=94, ...
  Lignes_Depense(tableRef=14): Refacturable=131, ...
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def apply(actions):
    """Envoie des actions vers l'endpoint /apply et renvoie le JSON de réponse."""
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    r.raise_for_status()
    return r.json()


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def get_views():
    return get_table("_grist_Views")


def get_sections():
    return get_table("_grist_Views_section")


def get_filters():
    return get_table("_grist_Filters")


def find_view(name):
    """Retourne l'id d'une vue portant ce nom, ou None (idempotence)."""
    for rec in get_views():
        if rec["fields"].get("name") == name:
            return rec["id"]
    return None


def section_of_view(view_id):
    """Retourne l'id de la première section de la vue donnée."""
    for rec in get_sections():
        if rec["fields"].get("parentId") == view_id:
            return rec["id"]
    return None


def create_view(table_id, name, col_ref=None, filter_obj=None):
    """
    Crée une vue raw_data sur la table si elle n'existe pas déjà, lui ajoute un
    filtre si fourni. Renvoie (view_id, section_id).
    """
    existing = find_view(name)
    if existing is not None:
        sid = section_of_view(existing)
        print(f"   ℹ️  Vue '{name}' existe déjà (view={existing}, section={sid})")
        return existing, sid

    result = apply([["AddView", table_id, "raw_data", name]])["retValues"][0]
    view_id, section_id = result["id"], result["sections"][0]
    if col_ref is not None and filter_obj is not None:
        add_filter(section_id, col_ref, filter_obj)
    return view_id, section_id


def add_filter(section_id, col_ref, filter_obj, pinned=True):
    """Ajoute un filtre à une section via la table _grist_Filters."""
    apply([[
        "AddRecord", "_grist_Filters", None,
        {
            "viewSectionRef": section_id,
            "colRef": col_ref,
            "filter": json.dumps(filter_obj),
            "pinned": pinned,
        },
    ]])


def show_section_fields(section_id):
    """Retourne les champs (colRef) d'une section via _grist_Views_section_fields."""
    r = requests.get(
        f"{BASE_URL}/api/docs/{DOC_ID}/tables/_grist_Views_section_fields/records",
        headers=H,
    )
    r.raise_for_status()
    return [rec for rec in r.json().get("records", [])
            if rec["fields"].get("parentId") == section_id]


def main():
    print("=" * 60)
    print("📄 Création des pages/vues du document Grist")
    print("=" * 60)

    # Vue "Devis" : Documents filtré sur Type=devis (col 88)
    print("\n📋 Page 'Devis'...")
    view_id, section_id = create_view("Documents", "Devis", 88, {"included": ["devis"]})
    print(f"   ✅ Devis (view={view_id}, section={section_id}, filtre Type=devis)")

    # Vue "Factures" : Documents filtré sur Type=facture (col 88)
    print("📋 Page 'Factures'...")
    view_id, section_id = create_view("Documents", "Factures", 88, {"included": ["facture"]})
    print(f"   ✅ Factures (view={view_id}, section={section_id}, filtre Type=facture)")

    # Vue "Refacturation" : Lignes_Depense filtré sur Refacturable=true (col 131)
    print("📋 Page 'Refacturation'...")
    view_id, section_id = create_view("Lignes_Depense", "Refacturation", 131, {"included": [True]})
    print(f"   ✅ Refacturation (view={view_id}, section={section_id}, filtre Refacturable=true)")

    # Vue "Clients" : Personnes filtré sur Role=client (col 80)
    print("📋 Page 'Clients'...")
    view_id, section_id = create_view("Personnes", "Clients", 80, {"included": ["client"]})
    print(f"   ✅ Clients (view={view_id}, section={section_id}, filtre Role=client)")

    # Vue "Membres" : Personnes filtré sur Role=membre (col 80)
    print("📋 Page 'Membres'...")
    view_id, section_id = create_view("Personnes", "Membres", 80, {"included": ["membre"]})
    print(f"   ✅ Membres (view={view_id}, section={section_id}, filtre Role=membre)")

    # Vue "Projets" : Projets
    print("📋 Page 'Projets'...")
    view_id, section_id = create_view("Projets", "Projets")
    print(f"   ✅ Projets (view={view_id}, section={section_id})")

    # Vue "Dépenses" : Depenses
    print("📋 Page 'Dépenses'...")
    view_id, section_id = create_view("Depenses", "Dépenses")
    print(f"   ✅ Dépenses (view={view_id}, section={section_id})")

    print("\n" + "=" * 60)
    print("✅ Vues créées (idempotent)")
    print("=" * 60)


if __name__ == "__main__":
    main()
