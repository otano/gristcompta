#!/usr/bin/env python3
"""
Configure les libellés d'affichage (« Display column ») des colonnes de
référence du document Grist, afin que les personnes et projets s'affichent par
leur nom (et Prénom + Nom pour les personnes) au lieu de « Table(rowId) ».

Ce script :
1. Crée une colonne de formule `Nom_Complet` dans la table Personnes
   (= Prénom + Nom) si elle n'existe pas déjà.
2. Positionne le champ `visibleCol` de chaque colonne de référence sur la
   colonne de la table cible à utiliser comme libellé :
     - toute référence → Personnes   : Nom_Complet
     - toute référence → Projets     : Nom
     - toute référence → Documents   : Numero
     - Depenses.Justificatif         : Commentaire (Justificatifs)
     - Lignes_Depense.Depense        : Date (Depenses)

Idempotent : ré-exécutable sans erreur.
"""

import os
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def apply(actions):
    r = requests.post(f"{BASE_URL}/api/docs/{DOC_ID}/apply", headers=H, json=actions)
    r.raise_for_status()
    return r.json()


def get_table(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def col_ids():
    """Retourne {(table_internal_id, colId): col_global_id} à partir de la
    table système _grist_Tables_column."""
    out = {}
    for c in get_table("_grist_Tables_column"):
        f = c["fields"]
        out[(f.get("parentId"), f.get("colId"))] = c["id"]
    return out


def table_internal_id(table_id):
    for t in get_table("_grist_Tables"):
        if t["fields"].get("tableId") == table_id:
            return t["id"]
    return None


def ensure_nom_complet(cm):
    """Crée Nom_Complet (Prénom + Nom) dans Personnes si absent. Retourne son id."""
    personne_table = table_internal_id("Personnes")
    if (personne_table, "Nom_Complet") in cm:
        print("ℹ️  Colonne Nom_Complet déjà présente.")
        return cm[(personne_table, "Nom_Complet")]
    result = apply([[
        "AddColumn", "Personnes", "Nom_Complet",
        {"type": "Text", "isFormula": True,
         "formula": "$Prenom + \" \" + $Nom", "label": "Nom complet"},
    ]])
    col_id = result["retValues"][0]["colRef"]
    print(f"✅ Colonne Nom_Complet créée (id={col_id}).")
    return col_id


# (table, colonne, libellé) → (table cible, colId du libellé)
VISIBLE_MAP = {
    ("Documents", "Client"): ("Personnes", "Nom_Complet"),
    ("Documents", "Projet"): ("Projets", "Nom"),
    ("Documents", "Source"): ("Documents", "Numero"),
    ("Projets", "Client"): ("Personnes", "Nom_Complet"),
    ("Projets", "Responsable"): ("Personnes", "Nom_Complet"),
    ("Depenses", "Personne"): ("Personnes", "Nom_Complet"),
    ("Depenses", "Projet"): ("Projets", "Nom"),
    ("Depenses", "Justificatif"): ("Justificatifs", "Commentaire"),
    ("Lignes_Refacturation", "Depense"): ("Depenses", "Date"),
    ("Lignes_Depense", "Depense"): ("Depenses", "Date"),
    ("Lignes_Document", "Document"): ("Documents", "Numero"),
}


def resolve_visible_col(cm, target_table, target_col):
    """Résout l'id global d'une colonne cible. Retourne None si introuvable."""
    for (parent, col), col_id in cm.items():
        if col == target_col:
            parent_table = next(
                (t["fields"].get("tableId")
                 for t in get_table("_grist_Tables") if t["id"] == parent),
                None,
            )
            if parent_table == target_table:
                return col_id
    return None


def main():
    print("=" * 60)
    print("🖼️  Configuration des libellés d'affichage des références")
    print("=" * 60)

    cm = col_ids()
    nom_complet_id = ensure_nom_complet(cm)

    actions = []
    for (table, column), (target_table, target_col) in VISIBLE_MAP.items():
        try:
            columns = [
                c for c in
                requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table}/columns",
                             headers=H).json()["columns"]
                if c["id"] == column
            ]
        except Exception:
            continue
        if not columns:
            print(f"ℹ️  Colonne {table}.{column} absente, ignorée.")
            continue
        col_type = columns[0]["fields"].get("type", "")
        if not col_type.startswith("Ref"):
            continue

        visible_col = nom_complet_id if target_col == "Nom_Complet" \
            else resolve_visible_col(cm, target_table, target_col)
        if visible_col is None:
            print(f"⚠️  Impossible de résoudre le libellé pour {table}.{column}.")
            continue

        # Idempotence : on applique seulement si différent
        current = columns[0]["fields"].get("visibleCol")
        if current == visible_col:
            print(f"ℹ️  {table}.{column} → libellé déjà configuré.")
            continue

        actions.append(["ModifyColumn", table, column, {"visibleCol": visible_col}])
        print(f"🔧 {table}.{column} → libellé id {visible_col}.")

    if actions:
        apply(actions)
        print(f"✅ {len(actions)} colonne(s) configurée(s).")
    else:
        print("✅ Rien à faire.")


if __name__ == "__main__":
    main()
