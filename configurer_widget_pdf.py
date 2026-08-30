#!/usr/bin/env python3
"""
Configure les sections custom « Aperçu · PDF » dans les vues Devis et Factures.

Une section custom = un widget iframe (widget/generer_pdf.html) qui affiche la
fiche document sélectionnée (devis ou facture) mise en forme, avec un bouton
« Imprimer / Enregistrer en PDF » (window.print).

Idempotent : si une section custom du même titre existe dans une vue, l'URL est
simplement mise à jour.
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

SECTION_TITLE = "Aperçu · PDF"
VIEWS = ["Devis", "Factures"]


def apply(actions, attempts=2):
    """Envoie des actions vers /apply (retry une fois sur erreur 5xx
    transitoire, ex. recalcul du doc)."""
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


def find_custom_section(view_id, title):
    for rec in get_sections():
        f = rec["fields"]
        if f.get("parentId") == view_id and f.get("title") == title:
            return rec
    return None


def find_grid_section(view_id, exclude_id):
    """Grille (section source) de la vue = section du plus petit id (créée en
    premier par creer_vues.py), hors section custom elle-même."""
    best = None
    for rec in get_sections():
        f = rec["fields"]
        if f.get("parentId") == view_id and rec["id"] != exclude_id:
            if best is None or rec["id"] < best:
                best = rec["id"]
    return best


def link_to_grid(section_id, view_id):
    """Relie le widget custom à la grille de la vue (linkSrcSectionRef) pour qu'il
    suive la sélection. Une section créée par AddViewSection n'est PAS liée."""
    for rec in get_sections():
        if rec["id"] == section_id and rec["fields"].get("linkSrcSectionRef"):
            print(f"   (déjà liée à la grille sect. {rec['fields']['linkSrcSectionRef']})")
            return
    grid = find_grid_section(view_id, section_id)
    if grid is None:
        print("   ⚠️  aucune grille trouvée pour lier le widget")
        return
    apply([["UpdateRecord", "_grist_Views_section", section_id, {"linkSrcSectionRef": grid}]])
    print(f"   ✅ widget lié à la grille (section {grid}) — la sélection pilote l'aperçu")


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


def update_section_options(section_id, title, url):
    apply([[
        "UpdateRecord", "_grist_Views_section", section_id,
        {
            "title": title,
            "options": json.dumps(custom_options(url)),
        },
    ]])


def configure_view(view_name):
    view_id = find_view(view_name)
    if view_id is None:
        print(f"❌ Vue '{view_name}' introuvable. Lance d'abord creer_vues.py")
        return

    existing = find_custom_section(view_id, SECTION_TITLE)
    if existing:
        print(f"ℹ️  Section custom '{SECTION_TITLE}' existante dans '{view_name}' "
              f"(section={existing['id']})")
        update_section_options(existing["id"], SECTION_TITLE, WIDGET_URL)
        print(f"✅ URL mise à jour pour '{view_name}'.")
        link_to_grid(existing["id"], view_id)
        return

    result = apply(["AddViewSection", SECTION_TITLE, "custom", view_id, "Documents"])
    section_id = result["retValues"][0]["id"]
    update_section_options(section_id, SECTION_TITLE, WIDGET_URL)
    print(f"✅ Section custom '{SECTION_TITLE}' créée dans '{view_name}' "
          f"(section={section_id}), URL configurée.")
    link_to_grid(section_id, view_id)


def main():
    print("=" * 60)
    print("🖨️  Configuration des sections « Aperçu · PDF » (Devis & Factures)")
    print("=" * 60)
    print(f"URL du widget : {WIDGET_URL}\n")

    for view in VIEWS:
        configure_view(view)

    print("\n✅ Configuration terminée (idempotent)")


if __name__ == "__main__":
    main()