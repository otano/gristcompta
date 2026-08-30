#!/usr/bin/env python3
"""
Configure la page « Créer un devis » du document Grist.

La page (vue « Créer un devis » sur Documents) contient 3 sections :
  1. « Formulaire devis » — Card natif Grist (type 'single') : fiche d'un seul
     devis, éditable, avec navigation ◂▸ et bouton « + » pour créer un devis.
     Filtré sur Type=devis.
  2. « Lignes du devis » — grille Lignes_Document (type 'record'), liée au
     formulaire via la colonne Document : n'affiche que les lignes du devis
     courant et pré-remplit la référence à l'ajout d'une ligne.
  3. « Aperçu · PDF » — widget custom generer_pdf.html, lié au formulaire :
     aperçu + impression du devis courant.

Disposition (via _grist_Views.layoutSpec, layout natif Grist) :
    ┌ form ──────────┬────────┐
    ├ lignes ────────┤  PDF   │
    └────────────────┴────────┘

Valeurs par défaut des nouveaux devis (trigger formulas « apply to new
records » de la colonne) : Type=devis, Date=aujourd'hui,
Date_Echeance=+30 j, Statut=brouillon. Une valeur fournie explicitement à la
création (ex. Type=facture par le widget de facturation) n'est pas écrasée.

Idempotent : la vue, les sections, les liaisons, le layout et les valeurs par
défaut sont recréés/mis à jour à chaque exécution.
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# URL publique où est hébergé widget/generer_pdf.html.
WIDGET_URL = os.environ.get(
    "GRIST_WIDGET_URL_PDF",
    "https://otano.github.io/gristcompta/widget/generer_pdf.html",
)

VIEW_NAME = "Créer un devis"
# (clé, titre de section, type Grist, table)
SECTIONS = [
    ("form", "Formulaire devis", "single", "Documents"),
    ("lignes", "Lignes du devis", "record", "Lignes_Document"),
    ("pdf", "Aperçu · PDF", "custom", "Documents"),
]

# Valeurs par défaut des nouveaux devis : colonne -> formule (trigger,
# recalculée seulement à la création d'un enregistrement).
DEFAULT_VALUES = [
    ("Type", "'devis'"),
    ("Date", "TODAY()"),
    ("Date_Echeance", "TODAY() + datetime.timedelta(days=30)"),
    ("Statut", "'brouillon'"),
]


def apply(actions, attempts=2):
    """Envoie des actions vers /apply (retry une fois sur erreur 5xx)."""
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


def get_views():
    return get_table("_grist_Views")


def get_sections():
    return get_table("_grist_Views_section")


def find_view(name):
    for rec in get_views():
        if rec["fields"].get("name") == name:
            return rec["id"]
    return None


def find_section(view_id, title):
    for rec in get_sections():
        f = rec["fields"]
        if f.get("parentId") == view_id and f.get("title") == title:
            return rec
    return None


def _tables_by_id():
    return {rec["id"]: rec["fields"].get("tableId") for rec in get_table("_grist_Tables")}


def get_col_ref(table_id, col_id):
    """Id numérique d'une colonne (via _grist_Tables_column)."""
    tables = _tables_by_id()
    for rec in get_table("_grist_Tables_column"):
        f = rec["fields"]
        if f.get("colId") == col_id and tables.get(f.get("parentId")) == table_id:
            return rec["id"]
    raise ValueError(f"Colonne {table_id}.{col_id} introuvable")


def get_table_ref(table_id):
    for rec in get_table("_grist_Tables"):
        if rec["fields"].get("tableId") == table_id:
            return rec["id"]
    raise ValueError(f"Table {table_id} introuvable")


def custom_options(url):
    """Options d'une section custom (customView = chaîne JSON échappée)."""
    return {
        "customView": json.dumps({
            "mode": "url",
            "url": url,
            "widgetDef": None,
            "access": "full",
            "pluginId": "",
            "sectionId": "",
            "renderAfterReady": True,
        })
    }


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


def remove_section_field(section_id, col_ref):
    """Retire un champ (colonne) affiché dans la section (card/grille)."""
    fields = get_table("_grist_Views_section_field")
    for rec in fields:
        f = rec["fields"]
        if f.get("parentId") == section_id and f.get("colRef") == col_ref:
            apply([["RemoveRecord", "_grist_Views_section_field", rec["id"]]])
            return


def main():
    print("=" * 60)
    print("📝 Configuration de la page « Créer un devis »")
    print("=" * 60)

    # 1. Vue (et retrait de la grille par défaut créée par AddView).
    view_id = find_view(VIEW_NAME)
    if view_id is None:
        result = apply([["AddView", "Documents", "raw_data", VIEW_NAME]])["retValues"][0]
        view_id, grid_id = result["id"], result["sections"][0]
        apply([["RemoveViewSection", grid_id]])
        print(f"✅ Vue '{VIEW_NAME}' créée (view={view_id}), grille par défaut retirée.")
    else:
        print(f"ℹ️  Vue '{VIEW_NAME}' existante (view={view_id}).")

    # 2. Sections (création si absentes, sinon réutilisation).
    ids = {}
    for key, title, stype, table in SECTIONS:
        existing = find_section(view_id, title)
        if existing:
            ids[key] = existing["id"]
            print(f"   ℹ️  Section '{title}' existante (section={existing['id']}).")
        else:
            got = apply([["AddViewSection", title, stype, view_id, table]])["retValues"][0]
            ids[key] = got["id"]
            print(f"   ✅ Section '{title}' créée (section={got['id']}, type={stype}).")

    card, lignes, pdf = ids["form"], ids["lignes"], ids["pdf"]

    # 3. Le formulaire doit être une Card unique ('single') : seul ce type
    #    affiche la navigation ◂▸ et le bouton « + » de création de devis.
    #    ('detail' = Card List : liste de cartes, pas de bouton « + ».)
    cur = next(s for s in get_sections() if s["id"] == card)["fields"].get("parentKey")
    if cur != "single":
        apply([["UpdateRecord", "_grist_Views_section", card, {"parentKey": "single"}]])
        print("   ✅ Formulaire converti en Card unique (parentKey='single').")
    else:
        print("   ℹ️  Formulaire déjà en Card unique (parentKey='single').")

    # 4. Liaison des sections au formulaire (source de sélection).
    lignes_doc_ref = get_col_ref("Lignes_Document", "Document")
    apply([[
        "UpdateRecord", "_grist_Views_section", lignes,
        {"linkSrcSectionRef": card, "linkSrcColRef": lignes_doc_ref},
    ]])
    apply([["UpdateRecord", "_grist_Views_section", pdf, {
        "linkSrcSectionRef": card,
        "title": "Aperçu · PDF",
        "options": json.dumps(custom_options(WIDGET_URL)),
    }]])
    print("   ✅ Lignes et PDF liés au formulaire (linkSrcSectionRef).")
    print(f"   ✅ Widget PDF configuré : {WIDGET_URL}")

    # 4. Le formulaire ne navigue que parmi les devis + champs utiles.
    type_ref = get_col_ref("Documents", "Type")
    add_filter(card, type_ref, {"included": ["devis"]})
    remove_section_field(card, get_col_ref("Documents", "Source"))
    print("   ✅ Formulaire filtré sur Type=devis, champ 'Source' retiré.")

    # 5. Disposition : formulaire + lignes à gauche, PDF à droite.
    # NB : layoutSpec est une colonne JSON lue par le client Grist. L'envoyer
    # comme dict Python via /apply la stocke en « repr » (guillemets simples)
    # -> le document ne se charge plus (erreur JSON position 1 mode récupération).
    # Toujours envoyer une chaîne json.dumps().
    layout = {
        "children": [{
            "children": [
                {"children": [
                    {"leaf": card, "size": 60},
                    {"leaf": lignes, "size": 40},
                ], "size": 70},
                {"leaf": pdf, "size": 30},
            ]
        }],
        "collapsed": [],
    }
    apply([["UpdateRecord", "_grist_Views", view_id, {"layoutSpec": json.dumps(layout)}]])
    print("   ✅ Layout : formulaire/lignes à gauche, PDF à droite.")

    # 6. Valeurs par défaut des nouveaux devis (trigger « new records »).
    # NB : on n'envoie que formula + recalcWhen ; recalcDeps (liste vide) est
    # déjà la valeur par défaut et le passer via l'API fait échouer le sandbox
    # (AssertionError sur la conversion RefList).
    actions = [[
        "ModifyColumn", "Documents", col,
        {"formula": expr, "recalcWhen": 0},
    ] for col, expr in DEFAULT_VALUES]
    apply(actions)
    print("   ✅ Par défaut : Type=devis, Date=aujourd'hui, "
          "Échéance=+30 j, Statut=brouillon (modifiables).")

    print("\n" + "=" * 60)
    print("✅ Page « Créer un devis » configurée (idempotent)")
    print("=" * 60)


if __name__ == "__main__":
    main()