#!/usr/bin/env python3
"""
Configure la page « Tableau de bord » (widget custom widget/tableau_de_bord.html)
: vue dédiée sur Projets avec UNE seule section custom plein écran pour suivre
par projet les dépenses, la part de chacun (camembert), le facturé et les
remboursements (effectués / à effectuer).

Idempotent : si la vue « Tableau de bord » existe, l'URL du widget est mise à
jour (et la grille par défaut est retirée si elle traîne encore).
"""

import os
import json
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# URL publique où est hébergé widget/tableau_de_bord.html.
WIDGET_URL = os.environ.get(
    "GRIST_WIDGET_URL_DASHBOARD",
    "https://otano.github.io/gristcompta/widget/tableau_de_bord.html",
)

VIEW_NAME = "Tableau de bord"
SECTION_TITLE = "Tableau de bord"


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


def get_table_ref(table_id):
    for rec in get_table("_grist_Tables"):
        if rec["fields"].get("tableId") == table_id:
            return rec["id"]
    raise ValueError(f"Table {table_id} introuvable")


def find_custom_section(view_id, title):
    for rec in get_sections():
        f = rec["fields"]
        if f.get("parentId") == view_id and f.get("title") == title:
            return rec
    return None


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


def remove_grid_section(view_id):
    """Retire les sections non-custom de la vue (le widget doit rester seul).

    Aucun record n'est touché : c'est un simple retrait de widget de la page.
    Ré-exécutable : une vue déjà propre n'a plus rien à retirer.
    """
    removed = False
    try:
        for rec in get_sections():
            f = rec["fields"]
            if f.get("parentId") == view_id and f.get("title") != SECTION_TITLE:
                apply([["RemoveViewSection", rec["id"]]])
                removed = True
                print(f"   ℹ️  Section reliquat retirée (section={rec['id']}, title={f.get('title')!r})")
    except Exception as e:
        print(f"   ⚠️  Impossible de retirer une section (action indisponible) : {e}")
    return removed


def ensure_dashboard_page():
    view_id = find_view(VIEW_NAME)
    if view_id is None:
        result = apply([["AddView", "Projets", "raw_data", VIEW_NAME]])["retValues"][0]
        view_id = result["id"]
        print(f"✅ Vue '{VIEW_NAME}' créée (view={view_id}).")
    else:
        print(f"ℹ️  Vue '{VIEW_NAME}' déjà présente (view={view_id}).")

    existing = find_custom_section(view_id, SECTION_TITLE)
    if existing:
        section_id = existing["id"]
        print(f"ℹ️  Section custom existante (section={section_id}), mise à jour de l'URL.")
        apply([[
            "UpdateRecord", "_grist_Views_section", section_id,
            {"title": SECTION_TITLE, "options": json.dumps(custom_options(WIDGET_URL))},
        ]])
    else:
        result = apply([["AddViewSection", SECTION_TITLE, "custom", view_id, "Projets"]])
        section_id = result["retValues"][0]["id"]
        apply([[
            "UpdateRecord", "_grist_Views_section", section_id,
            {"title": SECTION_TITLE, "options": json.dumps(custom_options(WIDGET_URL))},
        ]])
        print(f"✅ Section custom '{SECTION_TITLE}' créée (section={section_id}).")

    remove_grid_section(view_id)
    print(f"✅ Widget configuré : {WIDGET_URL}")


def main():
    print("=" * 60)
    print("📊 Configuration de la page « Tableau de bord »")
    print("=" * 60)
    print(f"URL du widget : {WIDGET_URL}\n")

    ensure_dashboard_page()

    print("\n✅ Configuration terminée (idempotent)")


if __name__ == "__main__":
    main()