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
| `setup_grist.py` | Crée les 8 tables. `Documents` unifie devis et factures (colonne `Type`) ; montant `Total` = formule sur `Lignes_Document` (asso **non soumise à la TVA** : pas de colonnes TVA/TTC). `Settings` = coordonnées de l'émetteur + IBAN/BIC (en-têtes et règlement PDF). |
| `creer_vues.py` | Crée les pages Devis, Factures, Refacturation, Projets, Dépenses avec leurs filtres. |
| `consolider_refacturation.py` | Consolide le flux achat → devis : passe Lignes_Depense en TTC, ajoute le lien vers le devis (`Document`), ajoute le projet hérité, les totaux, les alertes de cohérence, et crée une page « Refacturation · <Projet> » par projet. |
| `numerotation.py` | Configure la numérotation automatique `DEV-AAAA-NNN` / `FAC-AAAA-NNN` (par année et par type). |
| `configurer_widget.py` | Ajoute/config la section custom « Créer une facture depuis un devis » dans la vue Devis. |
| `configurer_widget_pdf.py` | Ajoute les sections « Aperçu · PDF » dans les vues Devis et Factures. |

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
source .env && uv run python consolider_refacturation.py
source .env && uv run python configurer_affichage.py
GRIST_WIDGET_URL="https://<url-publique>/creer_facture.html" uv run python configurer_widget.py
```

## Sécurité

les scripts lisent `GRIST_API_TOKEN` depuis les
variables d'environnement.
