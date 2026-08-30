#!/usr/bin/env python3
"""
Script de configuration du document Grist pour la gestion financière
du LabFab - Association 1901

Ce script crée et configure les tables nécessaires au suivi financier :
- Personnes (membres, clients, prestataires)
- Projets
- Documents (devis + factures unifiés)
- Lignes_Document
- Justificatifs
- Depenses
- Lignes_Depense
- Settings (coordonnées de l'émetteur pour les PDF)

Basé sur l'API Grist (https://support.getgrist.com/api/).

Remarque : la suppression de table n'a pas de endpoint REST dédié ;
on utilise l'endpoint /apply avec l'action RemoveTable.
"""

import os
import requests
from typing import Dict, List, Any


class GristAPI:
    """Client minimal pour l'API Grist."""

    def __init__(self):
        self.token = os.environ["GRIST_API_TOKEN"]
        self.doc_id = os.environ["GRIST_DOC_ID"]
        self.base_url = os.environ["GRIST_BASE_URL"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, data: Any = None) -> Any:
        url = f"{self.base_url}/api/docs/{self.doc_id}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, json=data
        )
        response.raise_for_status()
        return response.json() if response.text else None

    def create_table(self, table_id: str, columns: List[Dict]) -> None:
        """Crée une table avec ses colonnes (type + éventuellement formule)."""
        self._request("POST", "tables", {"tables": [{"id": table_id, "columns": columns}]})

    def add_columns(self, table_id: str, columns: List[Dict]) -> None:
        self._request("POST", f"tables/{table_id}/columns", {"columns": columns})

    def configure_columns(self, table_id: str, specs: List[Dict]) -> None:
        """
        Configure des colonnes via PATCH. Chaque spec : {id, fields}.
        fields peut contenir type, isFormula, formula, label, widgetOptions.
        Les éléments sont traités un par un pour éviter le bug
        "PATCH requires all records to have same fields".
        """
        for spec in specs:
            self._request(
                "PATCH",
                f"tables/{table_id}/columns",
                {"columns": [spec]},
            )

    def rename_column(self, table_id: str, col_id: str, new_label: str) -> None:
        self._request(
            "PATCH",
            f"tables/{table_id}/columns",
            {"columns": [{"id": col_id, "fields": {"label": new_label}}]},
        )

    def remove_column(self, table_id: str, col_id: str) -> None:
        self._request("POST", "apply", [["RemoveColumn", table_id, col_id]])

    def remove_table(self, table_id: str) -> None:
        self._request("POST", "apply", [["RemoveTable", table_id]])

    def get_tables(self) -> List[str]:
        return [t["id"] for t in self._request("GET", "tables")["tables"]]

    def get_columns(self, table_id: str) -> List[Dict]:
        return self._request("GET", f"tables/{table_id}/columns")["columns"]

    def add_records(self, table_id: str, records: List[Dict]) -> List[Dict]:
        return self._request(
            "POST", f"tables/{table_id}/records", {"records": [{"fields": r} for r in records]}
        )

    def get_records(self, table_id: str) -> List[Dict]:
        return self._request("GET", f"tables/{table_id}/records")["records"]


# ---------------------------------------------------------------------------
# Définition des colonnes
# ---------------------------------------------------------------------------

TYPE_CHOICES = {
    "role": {"choices": ["membre", "client", "prestataire"]},
    "statut_projet": {"choices": ["en_cours", "termine", "archive"]},
    "type_doc": {"choices": ["devis", "facture"]},
    "statut_doc": {
        "choices": [
            "brouillon", "envoye", "accepte", "refuse",
            "expire", "payee", "en_retard", "annulee",
        ]
    },
    "mode_paiement": {"choices": ["virement", "cheque", "especes", "carte"]},
    "type_depense": {"choices": ["note_frais", "commande"]},
    "statut_depense": {"choices": ["a_valider", "validee", "remboursee"]},
}


def choice_options(name: str) -> str:
    import json
    return json.dumps(TYPE_CHOICES[name])


# ---------------------------------------------------------------------------
# Définition des tables
# ---------------------------------------------------------------------------

PERSONNES_COLUMNS = [
    {"id": "Nom", "type": "Text"},
    {"id": "Prenom", "type": "Text"},
    {"id": "Email", "type": "Text"},
    {"id": "Telephone", "type": "Text"},
    {"id": "Role", "type": "Choice", "widgetOptions": choice_options("role")},
    {"id": "Actif", "type": "Bool"},
]

PROJETS_COLUMNS = [
    {"id": "Nom", "type": "Text"},
    {"id": "Client", "type": "Ref", "refTable": "Personnes"},
    {"id": "Responsable", "type": "Ref", "refTable": "Personnes"},
    {"id": "Budget_Prevu", "type": "Numeric"},
    {"id": "Date_Debut", "type": "Date"},
    {"id": "Date_Fin", "type": "Date"},
    {"id": "Statut", "type": "Choice", "widgetOptions": choice_options("statut_projet")},
    {"id": "Actif", "type": "Bool"},
]

DOCUMENTS_COLUMNS = [
    {"id": "Type", "type": "Choice", "widgetOptions": choice_options("type_doc")},
    {"id": "Numero", "type": "Text"},
    {"id": "Date", "type": "Date"},
    {"id": "Date_Echeance", "type": "Date"},
    {"id": "Client", "type": "Ref", "refTable": "Personnes"},
    {"id": "Projet", "type": "Ref", "refTable": "Projets"},
    {"id": "Statut", "type": "Choice", "widgetOptions": choice_options("statut_doc")},
    {"id": "Source", "type": "Ref", "refTable": "Documents"},
    {"id": "Objet", "type": "Text"},
    {"id": "Conditions", "type": "Text"},
    {"id": "Mode_Paiement", "type": "Choice", "widgetOptions": choice_options("mode_paiement")},
    {
        "id": "Total",
        "type": "Numeric",
        "isFormula": True,
        "formula": "SUM(Lignes_Document.lookupRecords(Document=$id).Montant)",
        "label": "Total",
    },
]

LIGNES_DOCUMENT_COLUMNS = [
    {"id": "Document", "type": "Ref", "refTable": "Documents"},
    {"id": "Description", "type": "Text"},
    {"id": "Quantite", "type": "Numeric"},
    {"id": "Unite", "type": "Text"},
    {"id": "Prix_unitaire", "type": "Numeric", "label": "Prix unitaire"},
    {"id": "Ordre", "type": "Numeric"},
    {"id": "Montant", "type": "Numeric", "isFormula": True, "formula": "$Quantite * $Prix_unitaire", "label": "Montant"},
]

JUSTIFICATIFS_COLUMNS = [
    {"id": "Fichier", "type": "Attachments"},
    {"id": "Date", "type": "Date"},
    {"id": "Commentaire", "type": "Text"},
]

DEPENSES_COLUMNS = [
    {"id": "Type_Depense", "type": "Choice", "widgetOptions": choice_options("type_depense")},
    {"id": "Personne", "type": "Ref", "refTable": "Personnes"},
    {"id": "Projet", "type": "Ref", "refTable": "Projets"},
    {"id": "Date", "type": "Date"},
    {"id": "Montant", "type": "Numeric"},
    {"id": "Statut", "type": "Choice", "widgetOptions": choice_options("statut_depense")},
    {"id": "Justificatif", "type": "Ref", "refTable": "Justificatifs"},
    {"id": "Date_Remboursement", "type": "Date"},
]

LIGNES_DEPENSE_COLUMNS = [
    {"id": "Depense", "type": "Ref", "refTable": "Depenses"},
    {"id": "Description", "type": "Text"},
    {"id": "Quantite", "type": "Numeric"},
    {"id": "Prix_Unitaire_HT", "type": "Numeric"},
    {"id": "Refacturable", "type": "Bool"},
    {"id": "Taux_Marge", "type": "Numeric"},
    {
        "id": "Prix_Refacture_HT",
        "type": "Numeric",
        "isFormula": True,
        "formula": "$Prix_Unitaire_HT * (1 + $Taux_Marge)",
    },
]

SETTINGS_COLUMNS = [
    {"id": "Raison_Sociale", "type": "Text"},
    {"id": "Adresse", "type": "Text"},
    {"id": "Ville_CP", "type": "Text"},
    {"id": "Email", "type": "Text"},
    {"id": "Telephone", "type": "Text"},
    {"id": "SIRET", "type": "Text"},
    {"id": "IBAN", "type": "Text"},
    {"id": "BIC", "type": "Text"},
]


# ---------------------------------------------------------------------------
# Rôles par table pour la création
# ---------------------------------------------------------------------------

ALL_TABLES = {
    "Settings": SETTINGS_COLUMNS,
    "Personnes": PERSONNES_COLUMNS,
    "Projets": PROJETS_COLUMNS,
    "Documents": DOCUMENTS_COLUMNS,
    "Lignes_Document": LIGNES_DOCUMENT_COLUMNS,
    "Justificatifs": JUSTIFICATIFS_COLUMNS,
    "Depenses": DEPENSES_COLUMNS,
    "Lignes_Depense": LIGNES_DEPENSE_COLUMNS,
}


def create_all_tables(grist: GristAPI) -> None:
    """Crée toutes les tables manquantes dans l'ordre de dépendance."""
    order = [
        "Settings",     # aucune dépendance
        "Personnes",    # aucune dépendance
        "Projets",     # dépend de Personnes
        "Documents",   # dépend de Personnes et Projets
        "Lignes_Document",  # dépend de Documents
        "Justificatifs",    # aucune dépendance
        "Depenses",         # dépend de Personnes, Projets, Justificatifs
        "Lignes_Depense",   # dépend de Depenses
    ]
    existing = grist.get_tables()
    for table in order:
        if table not in existing:
            grist.create_table(table, ALL_TABLES[table])
            print(f"✅ Table {table} créée")
        else:
            print(f"ℹ️  Table {table} existe déjà")


def main():
    print("=" * 60)
    print("🚀 Configuration du document Grist - LabFab")
    print("=" * 60)

    grist = GristAPI()
    create_all_tables(grist)

    print("\nTables finales :")
    for table in grist.get_tables():
        print(f"  - {table}")

    print("\n✅ Configuration terminée")


if __name__ == "__main__":
    main()
