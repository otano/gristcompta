# gristcompta

Configuration des tables, vues et d'un widget de facturation Grist pour la
comptabilité de l'association **LabFab** (loi 1901).

Le document Grist (`docs.getgrist.com`) est alimenté et structuré via l'API
REST Grist (`/api/docs/{docId}`).

## Principe

Les scripts suivants configurent le document Grist de manière **idempotente**
(peuvent être relancés sans effet de bord).

| Script | Rôle |
| --- | --- |
| `setup_grist.py` | Crée les 7 tables (Personnes, Projets, Documents, Lignes_Document, Justificatifs, Depenses, Lignes_Depense) avec colonnes et formules de totaux. |
| `creer_vues.py` | Crée les pages Devis, Factures, Refacturation, Trésorerie, Clients, Membres, Projets, Dépenses avec leurs filtres. |
| `numerotation.py` | Configure la numérotation automatique `DEV-AAAA-NNN` / `FAC-AAAA-NNN` (par année et par type). |
| `configurer_widget.py` | Ajoute/config la section custom « Créer une facture depuis un devis » dans la vue Devis. |

Le widget lui-même se trouve dans `widget/creer_facture.html` (fichier autonome
utilisant la Grist widget API) — voir `widget/README.md`.

## Prérequis

- `uv` comme gestionnaire de paquets (Python 3.13, voir `pyproject.toml`).
- L'instance et le document Grist accessibles.

## Installation

```bash
uv sync
cp .env.example .env   # puis renseigne les variables (jamais committées)
```

Les scripts lisent les credentials depuis l'environnement :
`GRIST_API_TOKEN`, `GRIST_DOC_ID`, `GRIST_BASE_URL` (et `GRIST_WIDGET_URL`
pour le widget).

## Usage

```bash
source .env && uv run python setup_grist.py
source .env && uv run python creer_vues.py
source .env && uv run python numerotation.py
GRIST_WIDGET_URL="https://<url-publique>/creer_facture.html" uv run python configurer_widget.py
```

## Sécurité

les scripts lisent `GRIST_API_TOKEN` depuis les
variables d'environnement.
