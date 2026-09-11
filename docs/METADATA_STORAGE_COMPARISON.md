# Comparaison des Solutions de Stockage des Métadonnées d'Images

## Contexte

SketchBook doit permettre de :
- Créer une bibliothèque d'images personnelle avec des tags
- Modifier facilement les tags (ajouter, supprimer)
- Exporter des lots d'images pour partager avec d'autres utilisateurs (avec les tags déjà assignés)

## Solutions Comparées

### 1. JSON Séparé (Solution Actuelle)

**Principe** : Stockage des métadonnées dans un fichier JSON séparé (`images.json`)

#### ✅ Avantages

- **Performance de lecture/écriture** : Accès rapide sans ouvrir les fichiers images
- **Simplicité** : Format lisible et facile à déboguer
- **Flexibilité** : Structure de données facilement extensible
- **Sécurité** : Pas de modification des fichiers images originaux
- **Backup facile** : Un seul fichier à sauvegarder pour toutes les métadonnées
- **Recherche rapide** : Indexation et recherche dans un seul fichier
- **Historique** : Facile de tracker les changements avec Git (si nécessaire)
- **Pas de dépendance aux formats** : Fonctionne avec tous les formats d'images

#### ❌ Inconvénients

- **Synchronisation** : Risque de désynchronisation si images déplacées/supprimées
- **Portabilité limitée** : Les tags ne voyagent pas avec les images lors de l'export
- **Duplication** : Métadonnées stockées à deux endroits (JSON + potentiellement EXIF)
- **Dépendance au fichier** : Si le JSON est corrompu/perdu, toutes les métadonnées sont perdues
- **Partage complexe** : Nécessite d'exporter le JSON séparément avec les images

---

### 2. Métadonnées EXIF dans les Images

**Principe** : Stockage des tags directement dans les métadonnées EXIF des fichiers images

#### ✅ Avantages

- **Portabilité maximale** : Les tags voyagent automatiquement avec les images
- **Partage simplifié** : Un seul fichier à partager (image + tags)
- **Pas de désynchronisation** : Les métadonnées sont toujours avec l'image
- **Standard** : EXIF est un standard largement supporté
- **Compatibilité** : Beaucoup d'outils peuvent lire les métadonnées EXIF
- **Backup intégré** : Les métadonnées sont sauvegardées avec les images

#### ❌ Inconvénients

- **Performance** : Nécessite d'ouvrir chaque fichier image pour lire/écrire
- **Modification des originaux** : Altère les fichiers images (risque de corruption)
- **Limitations EXIF** : 
  - Pas tous les formats supportent EXIF (PNG par exemple)
  - Limite de taille pour les champs texte
  - Structure rigide (pas de données complexes)
- **Vitesse de recherche** : Doit scanner tous les fichiers pour rechercher
- **Complexité technique** : Gestion des différents formats (JPEG, PNG, etc.)
- **Risque de perte** : Si l'image est réencodée, les métadonnées peuvent être perdues
- **Outils externes** : Certains outils suppriment les métadonnées

---

### 3. Métadonnées XMP dans les Images

**Principe** : Stockage des tags dans les métadonnées XMP (Extensible Metadata Platform)

#### ✅ Avantages

- **Portabilité** : Les tags voyagent avec les images
- **Flexibilité** : Structure XML extensible, supporte des données complexes
- **Standard Adobe** : Bien supporté par les outils Adobe (Lightroom, Photoshop)
- **Support multi-formats** : Peut être embarqué dans JPEG, PNG (via sidecar), TIFF, etc.
- **Sidecar files** : Pour PNG, peut utiliser des fichiers `.xmp` séparés
- **Riche** : Supporte les structures de données complexes (listes, hiérarchies)

#### ❌ Inconvénients

- **Performance** : Plus lent que JSON (doit parser XML)
- **Complexité** : Plus complexe à implémenter que JSON
- **Modification des originaux** : Altère les fichiers (sauf sidecar)
- **Support variable** : Pas tous les outils supportent XMP correctement
- **Taille** : XML peut être plus volumineux que JSON
- **Sidecar files** : Pour PNG, nécessite des fichiers séparés (risque de perte)

---

### 4. Base de Données SQLite

**Principe** : Stockage des métadonnées dans une base de données SQLite locale

#### ✅ Avantages

- **Performance** : Très rapide pour les recherches et requêtes complexes
- **Intégrité** : Transactions, contraintes, relations
- **Scalabilité** : Gère facilement des milliers d'images
- **Requêtes complexes** : SQL permet des recherches avancées
- **Indexation** : Index automatiques pour performances optimales
- **Backup** : Un seul fichier `.db` à sauvegarder
- **Sécurité** : Pas de modification des fichiers images

#### ❌ Inconvénients

- **Portabilité** : Les tags ne voyagent pas avec les images
- **Complexité** : Plus complexe que JSON (nécessite ORM ou SQL)
- **Dépendance** : Si la DB est corrompue, perte de toutes les métadonnées
- **Partage** : Nécessite d'exporter la DB séparément
- **Migration** : Plus difficile à migrer/partager que JSON

---

### 5. Solution Hybride (JSON + Export XMP)

**Principe** : Stockage principal en JSON, export optionnel en XMP pour le partage

#### ✅ Avantages

- **Meilleur des deux mondes** : Performance JSON + portabilité XMP à l'export
- **Flexibilité** : Utilisateur choisit quand exporter avec métadonnées
- **Sécurité** : Les originaux ne sont pas modifiés en local
- **Performance locale** : Recherche rapide via JSON
- **Partage facile** : Export avec XMP pour partage
- **Rétrocompatibilité** : Peut lire les métadonnées XMP à l'import

#### ❌ Inconvénients

- **Complexité** : Nécessite deux systèmes (JSON + XMP)
- **Synchronisation** : Doit maintenir la cohérence entre JSON et XMP
- **Temps d'export** : L'export avec XMP prend plus de temps

---

## Tableau Comparatif

| Critère | JSON | EXIF | XMP | SQLite | Hybride |
|---------|------|------|-----|--------|---------|
| **Performance lecture** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Performance écriture** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Portabilité** | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| **Simplicité implémentation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Partage facile** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Sécurité originaux** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Recherche rapide** | ⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Support formats** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Extensibilité** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Maintenance** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

## Recommandation

### Décision actuelle : **SQLite local** (`config/library.db`)

Le catalogue d'images a quitté `images.json`. `ImageDatabase` garde le même cache
mémoire (filtres / tri inchangés) ; seules les lignes modifiées sont écrites.
Le schéma inclut déjà `libraries`, `vendors`, `entitlements` et une source de
tag (`user` / `vendor`) pour les packs achetés ou partagés. La taxonomie UI
reste dans `user_tags_config.json`. Un `images.json` existant est importé une
fois puis archivé.

L'export XMP / pack ZIP reste le bon complément pour le **partage fichier par
fichier** ; ce n'est pas encore implémenté.

### Alternatives selon les besoins

- **Partage d'une image isolée** : XMP / sidecar (plus tard)
- **Pack de bibliothèque** : ZIP + `library.db` (ou export JSON de secours)
- **Catalogue en ligne** : Postgres / Supabase ; SQLite reste le cache client

---

## Détails Techniques

### JSON (legacy)
- Format : `images.json` dans `config/` (migré vers SQLite au premier lancement)
- Structure : `{image_id: {metadata}}`
- Bibliothèque : `json` standard Python

### XMP
- Format : XMP embarqué (JPEG) ou sidecar `.xmp` (PNG)
- Bibliothèque : `pyexiv2` ou `Pillow` avec `piexif`
- Standard : ISO 16684-1

### SQLite (actuel)
- Format : `library.db` dans `config/`
- Bibliothèque : `sqlite3` (stdlib), WAL
- Schéma : `libraries`, `images`, `image_tags` (+ tables réservées marketplace)
- Accès : `core/db/` (`connection`, `schema`, `images_repository`, `migrate_json`)

---

## Conclusion

SQLite est le stockage local du catalogue. Il prépare le multi-bibliothèques et
un store plus tard, sans changer le filtrage UI. Le partage portable (XMP / pack)
reste une couche d'export à ajouter par-dessus.
