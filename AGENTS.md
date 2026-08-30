# gristcompta

Config comptable LabFab pilotée par API dans un document Grist (`docs.getgrist.com`).
Pas d'application serveur : le dépôt = scripts Python **idempotents** (ré-exécutables)
qui configurent un document en ligne + un widget statique autonome.

## Env & exécution

- Projet `uv`, Python 3.13 (`.python-version`), seule dépendance : `requests`.
- Credentials Grist dans `~/.zshrc` : `GRIST_API_TOKEN`, `GRIST_DOC_ID`
  (`5DHirv5u3G8QjS9CSKCn4G`), `GRIST_BASE_URL`. Jamais de hardcode.
- Lancer : `source ~/.zshrc && uv run python <script>.py`.
- Pas de tests ni de lint. Vérification = relancer le script (idempotent) puis
  contrôler le résultat dans Grist.

## Architecture & ordre d'exécution

1. `setup_grist.py` — crée les 8 tables. `Documents` unifie **devis et factures**
   (colonne `Type` : `devis`/`facture`) ; montant `Total` = formule sur
   `Lignes_Document` (asso **non soumise à la TVA** : pas de colonnes TVA/TTC).
   `Settings` = coordonnées de l'émetteur + IBAN/BIC (en-têtes et règlement PDF).
2. `creer_vues.py` — pages (Devis, Factures, Clients… = `AddView` + filtre
   `_grist_Filters`). `Numerotation.py`, `configurer_affichage.py` (libellés de réf)
   ensuite. Ordre : setup → vues → numérotation → affichage.
3. `configurer_settings.py` — remplit `Settings` (une ligne, modifiable dans Grist).
4. `configurer_widget.py` (facture depuis devis) et `configurer_widget_pdf.py`
   (sections « Aperçu · PDF » dans les vues Devis + Factures).
5. `widget/` — fichiers HTML autonomes (grist-plugin-api.js) ; pas servis par Grist.
   Hébergés sur GitHub Pages : pousser sur `main` déploie (build auto). URL :
   `https://otano.github.io/gristcompta/widget/...`.
   `generer_pdf.html` lit `Documents/Lignes_Document/Personnes/Settings` et exporte
   en PDF via `window.print()` + `@media print` (note « association non assujettie
   à la TVA », règlement virement IBAN/BIC) ; `creer_facture.html` duplique un
   devis en facture (lot atomique, réf négative).

## Pièges API Grist (durs à deviner, cf. git log)

- Modifier un record : `PATCH .../records/{id}` renvoie **404** → passer par
  `/apply` + `UpdateRecord`.
- `BulkAddRecord` : **chaque valeur** de `column_values` doit être une liste
  (sinon `TypeError`). Référence négative (`-1`) résolue dans le même lot =
  création d'un doc + ses lignes en un lot atomique.
- Affichage d'une réf = `visibleCol` (**id numérique** de `_grist_Tables_column`)
  **ET** l'affichage `SetDisplayFormula` (gristHelper_Display) — les deux, sinon
  la grille montre `1` / `Personne(1)`.
- `options.customView` d'une section custom = **chaîne JSON échappée** (json.dumps imbriqué).
- colRefs hardcodés (Type=88, Statut=94, Refacturable=131…) dépendent de l'ordre
  de création ; les relire depuis `_grist_Tables_column` si nécessaire.
- Dates envoyées en string `YYYY-MM-DD`.

## API widget (grist-plugin-api.js)

- `grist.docApi.fetchTable(id)` **ignore ses options** (filters/expandRefs) → table
  entière en valeurs brutes, format **columnar** (à retransposer) ; filtrer en JS.
- `grist.onRecord`/`fetchSelectedRecord` renvoient les refs en **valeurs affichées**
  (expandRefs) → pour les rowIds, recharger via `fetchTable`. Réf = `{rowId, tableId}`,
  Date = `["d", epochSecondes]`. Helpers `refToId()`/`toDateJS()` dans
  `widget/creer_facture.html`.

## Conventions

- Commits en français ; push direct sur `main` (dépôt public, pas de PR).
- `.env` et `session-*.md` (transcripts d'OpenCode) jamais committés.