# Widgets « Créer une facture depuis un devis » et « Aperçu · PDF » — installation

Deux widgets custom Grist, fichiers statiques autonomes hébergés sur **GitHub
Pages** (`https://otano.github.io/gristcompta/widget/...`).

## `creer_facture.html`

Depuis la vue **Devis**, sélectionner un devis puis cliquer sur un bouton crée sa
facture automatiquement : la facture est créée (mêmes client/projet/objet/conditions),
les lignes du devis sont copiées vers la facture, la numérotation `FAC-AAAA-NNN`
se calcule toute seule, et le devis passe au statut **accepté**.

## `generer_pdf.html`

Affiche le devis ou la facture sélectionné(e) mis(e) en forme (en-tête émetteur
issu de la table `Settings`, client, lignes, total, note « association non
assujettie à la TVA », règlement virement IBAN/BIC, pied de page) et permet de
l'exporter en PDF via **« Imprimer / Enregistrer en PDF »** (`window.print()` +
`@media print`).

Deux sections custom « Aperçu · PDF » sont ajoutées dans les vues **Devis** et
**Factures** par `configurer_widget_pdf.py` (le même widget gère les deux types).
Les coordonnées de l'en-tête et l'IBAN/BIC de règlement se règlent dans la table
`Settings` (1 ligne), remplie par `configurer_settings.py`.

Le logo de l'en-tête (`logo_labfab.jpg`, 300×300) est embarqué en base64 dans le
fichier HTML : pour le changer, remplacer `logo_labfab.jpg` puis ré-injecter sa
base64 à la place de `data:image/jpeg;base64,...` dans `<img class="logo-img">`.

## Principe commun

Grist ne peut pas héberger un fichier statique : le widget doit être servi à une
**URL publique accessible en https** par `docs.getgrist.com`. La section custom
créée dans le document charge cette URL dans une iframe et se connecte au document
via l'API widget.

## 1. Héberger les fichiers des widgets

Le code est dans `widget/*.html` (fichiers autonomes, aucune dépendance à installer).

**Hébergement actuel** : GitHub Pages, URL de base
`https://otano.github.io/gristcompta/widget/`.

GitHub Pages sert les fichiers `main`/racine du dépôt public `otano/gristcompta`.
Pour redéployer après une modification d'un `widget/*.html`, il suffit de pousser
le nouveau contenu sur `main` (le build Pages est automatique).

## 2. Configurer les URLs dans le document Grist

Depuis `~/.zshrc` (credentials déjà définis), lancer :

```bash
source ~/.zshrc
uv run python configurer_settings.py        # table Settings + coordonnées
uv run python configurer_widget.py          # section « Créer une facture depuis un devis »
uv run python configurer_widget_pdf.py      # sections « Aperçu · PDF » (Devis + Factures)
```

Chaque script est idempotent ; si une section du même titre existe déjà, seule
l'URL est mise à jour.
