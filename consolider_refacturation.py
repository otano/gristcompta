#!/usr/bin/env python3
"""
Consolide le flux refacturation : d'un achat d'un membre (Depenses /
Lignes_Depense) jusqu'au devis qui le facture.

Sur Lignes_Depense (association non assujettie à la TVA -> tout TTC) :
- renomme Prix_Unitaire_HT  -> Prix_unitaire
- renomme Prix_Refacture_HT -> Prix_Refacture (formule Prix_unitaire*(1+Taux_Marge))
- ajoute Document (Ref Documents) : le devis qui facture la ligne. SEULES les
  lignes Refacturable=true doivent en porter une (règle métier, contrôlée par
  la colonne Verif_Refacturation).
- ajoute Projet (formule $Depense.Projet) : projet hérité de la dépense parent,
  sert de base aux vues par projet.
- ajoute Total_Refacture (Quantite * Prix_Refacture) et Verif_Refacturation
  (alerte si une ligne non refacturable est liée à un devis, ou si une ligne
  refacturable n'en porte pas encore).

Crée en plus une page « Refacturation · <Projet> » par projet existant : grille
des lignes de dépense filtrée sur le projet, avec les totaux en bas de grille et
la colonne pour lier le devis.

Idempotent : ré-exécutable sans erreur (renommages/additions/vues déjà en place
=> rien ne se passe).
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

TABLE = "Lignes_Depense"

# (ancien nom, nouveau nom) — colonnes HT -> TTC
RENAMES = [
    ("Prix_Unitaire_HT", "Prix_unitaire"),
    ("Prix_Refacture_HT", "Prix_Refacture"),
]

ADD_COLUMNS = [
    ("Document", {
        "type": "Ref:Documents",
        "isFormula": False,
        "label": "Lié au devis",
    }),
    ("Projet", {
        "type": "Ref:Projets",
        "isFormula": True,
        "formula": "$Depense.Projet",
        "label": "Projet",
    }),
    ("Total_Refacture", {
        "type": "Numeric",
        "isFormula": True,
        "formula": "$Quantite * $Prix_Refacture",
        "label": "Total refacturé",
    }),
    ("Verif_Refacturation", {
        "type": "Text",
        "isFormula": True,
        "formula": (
            'if not $Refacturable and $Document:\n'
            '    return "Attention : ligne non refacturable liée à un devis"\n'
            'elif $Refacturable and not $Document:\n'
            '    return "À lier à un devis"\n'
            'return ""'
        ),
        "label": "Vérif. refacturation",
    }),
]


def apply(actions, attempts=2):
    for i in range(attempts):
        r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
        if r.status_code < 500 or i == attempts - 1:
            r.raise_for_status()
            return r.json()
    return None


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def get_columns(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/columns", headers=H)
    r.raise_for_status()
    return [c["id"] for c in r.json()["columns"]]


def get_views():
    return get_table("_grist_Views")


def find_view(name):
    for rec in get_views():
        if rec["fields"].get("name") == name:
            return rec["id"]
    return None


def get_col_ref(table_id, col_id):
    """Id numérique d'une colonne (via _grist_Tables_column)."""
    tables = {r["id"]: r["fields"].get("tableId") for r in get_table("_grist_Tables")}
    for rec in get_table("_grist_Tables_column"):
        f = rec["fields"]
        if f.get("colId") == col_id and tables.get(f.get("parentId")) == table_id:
            return rec["id"]
    raise ValueError(f"Colonne {table_id}.{col_id} introuvable")


def add_filter(section_id, col_ref, filter_obj):
    """Ajoute un filtre à une section (idempotent)."""
    for rec in get_table("_grist_Filters"):
        f = rec["fields"]
        if f.get("viewSectionRef") == section_id and f.get("colRef") == col_ref:
            return
    apply([["AddRecord", "_grist_Filters", None, {
        "viewSectionRef": section_id,
        "colRef": col_ref,
        "filter": json.dumps(filter_obj),
        "pinned": True,
    }]])


# Colonnes ajoutées à la grille « Refacturation » classique (en plus du max+1).
EXTRA_GRID_COLS = ["Document", "Projet", "Total_Refacture", "Verif_Refacturation"]


def add_extra_grid_cols():
    """Ajoute les nouvelles colonnes à la grille de la page 'Refacturation'."""
    view_id = find_view("Refacturation")
    if view_id is None:
        print("   ℹ️  Page 'Refacturation' introuvable, rien à compléter.")
        return
    # Section liée à cette vue, sur Lignes_Depense (grille).
    section = None
    for rec in get_table("_grist_Views_section"):
        f = rec["fields"]
        if f.get("parentId") == view_id and f.get("tableRef") == get_table_ref(TABLE):
            section = rec["id"]
            break
    if section is None:
        print("   ⚠️  aucune grille Lignes_Depense sur la page 'Refacturation'.")
        return

    field_recs = get_table("_grist_Views_section_field")
    col_ids = {
        c["id"]: c["fields"].get("colId")
        for c in get_table("_grist_Tables_column")
    }
    existing = {
        col_ids.get(sf["fields"].get("colRef"))
        for sf in field_recs if sf["fields"].get("parentId") == section
    }
    header_index = len(existing)
    for col in EXTRA_GRID_COLS:
        if col in existing:
            continue
        col_ref = get_col_ref(TABLE, col)
        apply([["AddRecord", "_grist_Views_section_field", None, {
            "parentId": section,
            "colRef": col_ref,
            "parentPos": header_index + 1,
            "width": 0,
        }]])
        header_index += 1
        print(f"   ✅ Colonne '{col}' ajoutée à la grille Refacturation.")


def get_table_ref(table_id):
    for rec in get_table("_grist_Tables"):
        if rec["fields"].get("tableId") == table_id:
            return rec["id"]
    raise ValueError(f"Table {table_id} introuvable")


def migrate_columns():
    """Passe Lignes_Depense au schéma TTC + liens refacturation (idempotent)."""
    print("\n1. Schéma de Lignes_Depense...")

    # Renommages HT -> TTC.
    for old, new in RENAMES:
        cols = get_columns(TABLE)
        if old not in cols:
            print(f"   ℹ️  Colonne {old} absente (déjà renommée en {new}).")
            continue
        apply([["RenameColumn", TABLE, old, new]])
        print(f"   ✅ Renommage {old} -> {new}.")

    # Formule de Prix_Refacture (re-appliquée après renommage).
    if "Prix_Refacture" in get_columns(TABLE):
        apply([["ModifyColumn", TABLE, "Prix_Refacture", {
            "isFormula": True,
            "formula": "$Prix_unitaire * (1 + $Taux_Marge)",
        }]])
        print("   ✅ Formule Prix_Refacture = Prix_unitaire * (1 + Taux_Marge).")
    else:
        print("   ⚠️  Colonne Prix_Refacture introuvable après renommage !")

    # Colonnes ajoutées si absentes.
    existing = set(get_columns(TABLE))
    for name, fields in ADD_COLUMNS:
        if name not in existing:
            apply([["AddColumn", TABLE, name, fields]])
            print(f"   ✅ Colonne {name} ajoutée.")
            continue
        # La colonne Document doit rester une donnée (sinon le lien au devis
        # serait écrasé à chaque recalcul). Repare si elle a été créée en
        # formule vide par erreur lors d'un premier passage.
        if name == "Document":
            apply([["ModifyColumn", TABLE, "Document", {
                "isFormula": False,
                "formula": "",
            }]])
        print(f"   ℹ️  Colonne {name} déjà présente.")

    return True


def create_project_views():
    """Crée une page « Refacturation · <Projet> » par projet (idempotent)."""
    print("\n2. Pages par projet...")
    projets = get_table("Projets")
    if not projets:
        print("   ℹ️  Aucun projet -> aucune page créée.")
        return

    projet_col_ref = get_col_ref(TABLE, "Projet")
    for p in projets:
        nom = p["fields"].get("Nom") or f"projet-{p['id']}"
        name = f"Refacturation · {nom}"
        if find_view(name) is not None:
            print(f"   ℹ️  Page '{name}' déjà présente.")
            continue
        result = apply([["AddView", TABLE, "raw_data", name]])["retValues"][0]
        section_id = result["sections"][0]
        add_filter(section_id, projet_col_ref, {"included": [p["id"]]})
        print(f"   ✅ Page '{name}' créée (filtre Projet={nom}, id={p['id']}).")


def main():
    print("=" * 60)
    print("🔗 Consolidation du flux refacturation")
    print("=" * 60)

    migrate_columns()
    add_extra_grid_cols()
    create_project_views()

    print("\n" + "=" * 60)
    print("✅ Consolidation terminée (idempotent)")
    print("=" * 60)


if __name__ == "__main__":
    main()