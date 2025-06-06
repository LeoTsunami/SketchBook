## Détection de doublons dans un système de gestion d'images

### Nom du projet et sous axe:
SketchBook - Système de détection de doublons d'images

### Objectifs:
- Implémenter un système fiable de détection des doublons d'images
- Éviter les faux positifs et les faux négatifs
- Maintenir de bonnes performances avec un grand nombre d'images
- Gérer les cas de fichiers renommés ou déplacés

### Enjeux:
- Garantir l'intégrité de la bibliothèque d'images
- Optimiser l'utilisation de l'espace de stockage
- Maintenir une expérience utilisateur fluide
- Assurer la traçabilité des images importées

### Verrous:
1. **Verrou technique : Fiabilité de la détection**
   - La comparaison bit à bit des fichiers est trop coûteuse en ressources
   - Le hachage des fichiers peut générer des faux positifs
   - Les métadonnées EXIF peuvent être incomplètes ou manquantes
   - Les modifications mineures (compression, redimensionnement) peuvent masquer des doublons réels

2. **Verrou méthodologique : Gestion des métadonnées**
   - Besoin de maintenir la cohérence entre les fichiers et la base de données
   - Nécessité de gérer les chemins de fichiers relatifs et absolus
   - Complexité de la synchronisation entre le stockage et les métadonnées

### Solutions envisagées:
1. **Approche par hachage de contenu**
   - Avantages : Détection précise des doublons exacts
   - Inconvénients : Coût en performance, ne détecte pas les variations mineures

2. **Comparaison des métadonnées EXIF**
   - Avantages : Rapide, détecte les images similaires
   - Inconvénients : Dépend de la présence des métadonnées

3. **Système hybride de métadonnées personnalisées** (Solution retenue)
   - Stockage du chemin original
   - Comparaison des caractéristiques essentielles (taille, dimensions, nom)
   - Base de données locale pour la persistance
   - Système de logging détaillé pour le débogage

### Conclusion:
La solution retenue combine plusieurs approches pour résoudre les verrous identifiés :
- Utilisation d'un système de métadonnées personnalisées pour une détection fiable
- Implémentation d'une détection en deux étapes (chemin exact puis métadonnées)
- Mise en place d'un système de logging détaillé pour la traçabilité
- Optimisation des performances par l'utilisation de métadonnées plutôt que le hachage

Cette approche a permis de résoudre les verrous techniques tout en maintenant de bonnes performances et une excellente fiabilité de détection. 