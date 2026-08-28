#!/usr/bin/env python3
"""
Crée un devis de test avec ses lignes dans le document Grist, pour tester le
widget « Créer une facture depuis un devis ».

Idempotent : si un devis avec le même objet existe déjà, il ne l'ajoute pas.
"""

import os
import requests

TOKEN = os.environ["GRIST_API_TOKEN"]
DOC_ID = os.environ["GRIST_DOC_ID"]
BASE_URL = os.environ["GRIST_BASE_URL"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

OBJET = "Devis test - impression 3D"

LIGNES = [
    {"Description": "Impression 3D pièce prototype (PLA)", "Quantite": 10, "Unite": "pièce", "Prix_Unitaire_HT": 15.0, "TVA": 0.20},
    {"Description": "Frais de machine (découpe laser)", "Quantite": 3, "Unite": "h", "Prix_Unitaire_HT": 40.0, "TVA": 0.20},
    {"Description": "Accompagnement / mise en route", "Quantite": 1, "Unite": "forfait", "Prix_Unitaire_HT": 120.0, "TVA": 0.20},
]


def get_records(table_id):
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/{table_id}/records", headers=H)
    r.raise_for_status()
    return r.json().get("records", [])


def main():
    print("=" * 60)
    print("📝 Création d'un devis de test avec ses lignes")
    print("=" * 60)

    # Idempotence : on ne crée que si aucun devis avec cet objet n'existe
    for doc in get_records("Documents"):
        if doc["fields"].get("Objet") == OBJET:
            print(f"ℹ️  Le devis existe déjà (id={doc['id']}, Numero={doc['fields'].get('Numero')})")
            return

    # 1. Créer le document devis
    fields = {
        "Type": "devis",
        "Client": 1,           # Laurent (premier contact disponible)
        "Projet": 1,           # oktobermake
        "Objet": OBJET,
        "Date": "2026-08-28",
        "Date_Echeance": "2026-09-27",
        "Statut": "envoye",
        "Conditions": "Paiement à réception de facture.",
        "Mode_Paiement": "virement",
    }
    r = requests.post(
        f"{BASE_URL}/api/docs/{DOC_ID}/tables/Documents/records",
        headers=H,
        json={"records": [{"fields": fields}]},
    )
    r.raise_for_status()
    devis_id = r.json()["records"][0]["id"]
    print(f"✅ Devis créé (id={devis_id}, Type=devis)")

    # 2. Créer les lignes du devis
    records = []
    for idx, ligne in enumerate(LIGNES, start=1):
        rec = dict(ligne)
        rec["Document"] = devis_id
        rec["Ordre"] = idx
        records.append({"fields": rec})

    r = requests.post(
        f"{BASE_URL}/api/docs/{DOC_ID}/tables/Lignes_Document/records",
        headers=H,
        json={"records": records},
    )
    r.raise_for_status()
    print(f"✅ {len(records)} lignes créées pour le devis {devis_id}")

    # 3. Vérifier les totaux calculés
    r = requests.get(f"{BASE_URL}/api/docs/{DOC_ID}/tables/Documents/records", headers=H)
    for doc in r.json()["records"]:
        if doc["id"] == devis_id:
            f = doc["fields"]
            print("\nRécapitulatif :")
            print(f"  Numero   : {f.get('Numero')}")
            print(f"  Total HT : {f.get('Total_HT')}")
            print(f"  Total TVA: {f.get('Total_TVA')}")
            print(f"  Total TTC: {f.get('Total_TTC')}")

    print("\nOuvre la page 'Devis', sélectionne ce devis, puis clique sur")
    print("« Créer la facture » dans le widget.")


if __name__ == "__main__":
    main()
