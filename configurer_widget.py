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
    "https://REMPLACER_PAR_L_URL_PUBLIQUE/creer_facture.html",
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
        return

    # Créer la section custom sur la vue "Devis"
    result = apply([["AddViewSection", SECTION_TITLE, "custom", view_id, "Documents"]])
    section_id = result["retValues"][0]["id"]
    print(f"✅ Section custom créée (section={section_id})")

    # Configurer les options customView
    update_section_options(section_id, SECTION_TITLE, WIDGET_URL)
    print("✅ Options customView configurées (accès complet).")
    print("ℹ️  Lancez la fonction GRIST_WIDGET_URL pour utiliser l'URL réelle.")


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
