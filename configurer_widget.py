#!/usr/bin/env python3
"""
Configure le widget custom « Créer une facture depuis un devis » dans le
document Grist.

Le widget est une page HTML/JS (widget/creer_facture.html) hébergée à une URL
publique accessible par l'instance Grist.

Ce script :
1. Ajoute une section custom (type 'custom') à la vue "Devis", sur la table
   Documents.
2. Configure les options de cette section (customView) pour pointer vers l'URL
   du widget, avec l'accès complet (le widget écrit dans le document).

Idempotent : si une section custom portant ce titre existe déjà dans la vue
"Devis", il l'utilise et ne fait que mettre à jour l'URL.
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# URL publique où est hébergé widget/creer_facture.html.
WIDGET_URL = os.environ.get(
    "GRIST_WIDGET_URL",
    "https://otano.github.io/gristcompta/widget/creer_facture.html",
)

SECTION_TITLE = "Créer une facture depuis un devis"


def apply(actions):
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
    print(f"   ✅ widget lié à la grille (section {grid})")


def custom_options(url):
    """Options d'une section custom.

    Dans les options d'une vue, le champ `customView` est une *chaîne JSON*
    imbriquée (et non un objet) : le client Grist appelle JSON.parse dessus.
    """
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


def main():
    print("=" * 60)
    print("🔌 Configuration du widget custom « Créer une facture depuis un devis »")
    print("=" * 60)
    print(f"URL du widget : {WIDGET_URL}")

    view_id = find_view("Devis")
    if view_id is None:
        print("❌ Vue 'Devis' introuvable. Lance d'abord creer_vues.py")
        return

    existing = find_custom_section(view_id, SECTION_TITLE)
    if existing:
        section_id = existing["id"]
        print(f"ℹ️  Section custom existante (section={section_id})")
        print("   Mise à jour des options (URL)...")
        update_section_options(section_id, SECTION_TITLE, WIDGET_URL)
        print("✅ Options mises à jour.")
        link_to_grid(section_id, view_id)
        return

    # Créer la section custom sur la vue "Devis"
    result = apply([["AddViewSection", SECTION_TITLE, "custom", view_id, "Documents"]])
    section_id = result["retValues"][0]["id"]
    print(f"✅ Section custom créée (section={section_id})")

    # Configurer les options customView
    update_section_options(section_id, SECTION_TITLE, WIDGET_URL)
    print("✅ Options customView configurées (accès complet).")
    link_to_grid(section_id, view_id)
    print(f"ℹ️  URL du widget : {WIDGET_URL}")


def update_section_options(section_id, title, url):
    """Met à jour le titre et les options customView d'une section via /apply."""
    apply([[
        "UpdateRecord", "_grist_Views_section", section_id,
        {
            "title": title,
            "options": json.dumps(custom_options(url)),
        },
    ]])


if __name__ == "__main__":
    main()
