# Widget « Créer une facture depuis un devis » — installation

Ce widget custom Grist permet, depuis la vue **Devis**, de sélectionner un devis
puis de cliquer sur un bouton pour créer sa facture automatiquement :
la facture est créée (mêmes client/projet/objet/conditions), les lignes du devis
sont copiées vers la facture, la numérotation `FAC-AAAA-NNN` se calcule toute
seule, et le devis passe au statut **accepté**.

## Principe

Grist ne peut pas héberger un fichier statique : le widget doit être servie à
une **URL publique accessible en https** par ton instance Grist
(`docs.getgrist.com`). La section custom créée dans le document charge
cette URL dans une iframe et se connecte au document via l'API widget.

## 1. Héberger le fichier du widget

Le code du widget est dans `widget/creer_facture.html` (fichier autonome,
aucune dépendance à installer).

Héberge-le sur n'importe quel hébergement statique qui fournit une URL https :

- **GitHub Pages** : place `creer_facture.html` dans un dépôt, active
  « Pages », l'URL sera `https://<user>.github.io/<repo>/creer_facture.html`.
- **Netlify Drop** : glisse le fichier sur app.netlify.com/drop → URL fournie.
- Un serveur statique (nginx, S3) ou l'outil `grist` self-hosted.

## 2. Configurer l'URL dans le document Grist

Le script `configurer_widget.py` crée/configure la section custom dans la vue
**Devis** (idempotent). Indique l'URL publique puis relance-le :

```bash
source ~/.zshrc
GRIST_WIDGET_URL="https://<url-publique>/creer_facture.html" \
  python3 configurer_widget.py
```

Il utilise les variables `GRIST_API_TOKEN`, `GRIST_DOC_ID`, `GRIST_BASE_URL`
(déjà définies dans `.zshrc`).

## 3. Utilisation

1. Ouvre la page **Devis** (la section « Créer une facture depuis un devis »
   s'affiche sous la grille).
2. Sélectionne un devis dans la grille.
3. Le widget affiche le résumé du devis (numéro, client, total, statut, nombre
   de lignes).
4. Clique sur **Créer la facture**.
5. La facture apparaît dans la page **Factures** avec ses lignes et son numéro
   automatique ; le devis passe à « accepté ».
