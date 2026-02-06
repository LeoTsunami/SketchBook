# Journal des modifications

## 2026-02-06 (nettoyage du code : suppression du code inutilisé et factorisation des doublons)
### ✅ Tâches :
- Nettoyage du code : suppression du code inutilisé, factorisation des doublons, amélioration de la maintenabilité

- **Code obsolète supprimé** : Suppression de `gui/session_dialog.py` (remplacé par `SessionSettingsDialog`). Suppression de la méthode `get_current_session()` et de l'attribut `current_session` non utilisés dans `SessionManager`. Suppression de la fonction `load_stylesheet()` dupliquée dans `gui/image_grid.py`.
- **Factorisation des utilitaires d'icônes** : Création de `gui/icon_utils.py` avec les fonctions centralisées `find_tag_icon()` et `invert_icon()`. Remplacement de 5 implémentations dupliquées de `_invert_icon()` et 4 implémentations dupliquées de `_find_tag_icon()` dans tout le codebase. Toute la gestion des icônes passe désormais par un module unique et bien documenté.
- **Nettoyage de SessionManager** : Suppression de la méthode `get_current_session()` non utilisée qui créait des classes dynamiques. Ajout de commentaires TODO pour la future implémentation de la persistance des presets et de l'historique des sessions. Conservation des chemins et structures de données pour l'intégration future de l'installer.
- **Migration de la recherche dépréciée** : Mise à jour de `ImageManager.search_images()` pour utiliser en interne `search_images_advanced()` pour la cohérence. Mise à jour de `gui/image_grid.py` pour utiliser directement `search_images_advanced()`.
- **Amélioration des fonctions de debug** : Documentation améliorée pour les fonctions `_dbg()` et `_dbg_space()` dans `slideshow_window.py` avec un contrôle clair basé sur des flags.
- **Documentation de l'API installer** : Documentation améliorée pour `set_user_data_directory()` et `get_user_data_directory()` dans `core/user_data.py` comme API publique pour les installers afin de configurer les chemins des données utilisateur.
 → Résultat : Le codebase est plus propre, plus maintenable, avec une duplication réduite. Toutes les fonctionnalités sont préservées. Prêt pour le déploiement avec installer avec chemins de données utilisateur configurables.
---

## 2026-02-05 (persistance du nombre de colonnes de la grille)
### ✅ Tâches :
- Sauvegarder le nombre de colonnes de la grille dans les paramètres utilisateur

- Lorsque l'utilisateur modifie le curseur du nombre de colonnes (3–10), la valeur est désormais enregistrée via `settings.save()` après `settings.set("ui.grid.columns", value)`. À la réouverture, le curseur et la grille utilisent `settings.get("ui.grid.columns", 4)` (déjà en place).
 → Résultat : Le nombre de colonnes choisi est restauré au prochain lancement.
---

## 2026-02-03 (bibliothèque de tags : modification des tags utilisateur)
### ✅ Tâches :
- Bibliothèque de tags : modification des tags utilisateur (tags par défaut en lecture seule). Renommer : clic droit sur un tag utilisateur → « Renommer... ». Glisser-déposer : déposer un tag sur une catégorie ou un autre tag pour le déplacer. Add tag : bouton pour ajouter un tag (nom + icône optionnelle). Persistance dans `user_tags_config.json` et `ImageDatabase.rename_tag()`.
 → Résultat : Organiser, renommer et ajouter des tags personnalisés depuis la bibliothèque.
---

## 2026-02-03 (grille d’images : chargement des pixmaps visibles uniquement, debounce)
### ✅ Tâches :
- Charger les pixmaps des miniatures uniquement pour les éléments visibles, avec QTimer pour éviter les lag sur le main thread

- Au scroll, plus d’appel direct à la détection de visibilité : `_on_scroll` ne fait que démarrer un timer de debounce (120 ms) ; à l’échéance, `_check_visible_thumbnails` s’exécute et met en file les IDs des images visibles dans `pending_load_queue` (plafonnée à 60).
- Un timer séparé `load_ticker_timer` (80 ms) traite la file : au plus 2 chargements par tick via `_process_pending_loads`, ce qui étale les chargements de pixmaps et les `set_image()` dans le temps et évite de surcharger le thread principal.
- `clear()` arrête désormais les deux timers et vide la file en attente.
 → Résultat : Le défilement de grandes grilles est beaucoup plus fluide ; les pixmaps se chargent progressivement pour les miniatures visibles uniquement.
---

## 2026-01-30 (largeur max dans les paramètres d'import)
### ✅ Tâches :
- Ajout de la largeur max dans les paramètres d'import d'images

- Fenêtre Paramètres : nouveau champ « Maximum Width » (360–4320 px, défaut 1920) dans la section Image Import Compression, à côté de Maximum Height.
- Redimensionnement à l'import : les images sont maintenant bornées par max_width et max_height (on utilise le plus petit des deux ratios pour ne dépasser aucune dimension). Le ratio d'aspect est conservé.
- Tests : `test_import_image_with_metadata` mis à jour pour vérifier les dimensions dans les limites par défaut et le ratio conservé (plus de constante MAX_WIDTH).
 → Résultat : L'utilisateur peut limiter largeur et hauteur des images importées.
---

## 2026-01-30 (Camera-Angle comme contrainte AND globale)
### ✅ Tâches :
- Camera-Angle et catégories « label » contraignent toutes les catégories (AND)

- Les catégories label (ex. « Camera-Angle: », « Miscellaneous: ») sont appliquées comme **AND global** en plus du filtre de catégorie. Exemple : Humain + Wide-Angle n’affiche que les images à la fois Humain et Wide-Angle.
- Logique dans `_filter_images_by_category` : d’abord les images qui matchent une catégorie active (avec sous-tags), puis on ne garde que celles qui ont aussi tous les tags des catégories label (constraining_tags). Sans catégorie sélectionnée, seuls ces tags s’appliquent (ex. Wide-Angle seul = toutes les images avec Wide-Angle).
 → Résultat : En choisissant une catégorie puis un angle de caméra, les résultats sont bien restreints à cette combinaison.
---

## 2026-01-30 (suppression de tag en arrière-plan)
### ✅ Tâches :
- Suppression de tag sur une ou plusieurs images déplacée en arrière-plan

- L’action « supprimer un tag » (bouton × sur les chips de tag des images sélectionnées) utilise maintenant le même worker que l’assignation : `TagApplyWorker` avec `operation="remove"` s’exécute dans le thread pool.
- `ImageGrid._remove_tag_from_selection` crée un `TagApplyWorker`, connecte progress/finished/error et le lance dans `thread_pool` ; les handlers `_on_remove_tag_finished` et `_on_remove_tag_error` s’exécutent sur le thread principal et rafraîchissent les miniatures ou émettent les erreurs.
- Nouveaux signaux sur `ImageGrid` : `tag_remove_progress`, `tag_remove_finished`, `tag_remove_error` pour que la fenêtre principale puisse afficher statut et progression (même UX que « Applying tag... »).
- La fenêtre principale se connecte à ces signaux et affiche « Removing tag 'X'... » avec barre de progression, puis nettoie à la fin ou en cas d’erreur.
- Tests unitaires dans `tests/test_tag_apply_worker.py` pour l’opération remove, liste vide et cas d’erreur.
 → Résultat : Supprimer un tag sur beaucoup d’images ne bloque plus l’interface ; même modèle de threading que pour l’assignation de tag.
---

## 2026-01-30
### ✅ Tâches :
- Décompte de session : seconde par seconde et dégradé rouge vers 0

- Le timer déclenche maintenant chaque seconde (intervalle 1 s) au lieu de 100 ms ; le décompte décroît seconde par seconde.
- L’overlay de décompte est passé de haut-droite à haut-gauche dans la fenêtre de session.
- La couleur du décompte varie progressivement vers le rouge quand le temps restant approche de 0 (thème sombre : blanc → rouge ; thème clair : noir → rouge). La couleur est réinitialisée au changement d’image ou au démarrage de session.
 → Résultat : Décompte plus lisible en haut à gauche, avec retour visuel d’urgence quand le temps diminue.
---

## 2026-01-27
### ✅ Tâches :
- Sessions de dessin (Course + intervalle constant)
- Affichage des tags sur les images sélectionnées dans la grille
- Fenêtre de paramètres et améliorations du menu

- **Sessions** : Session Settings lance maintenant une fenêtre de session dédiée.
  - **Course** : durée 10–60 min (pas de 10). Phases : WarmUp (30 s/image), Gesture (1 min/image), Anatomy (5 min/image), Shading (10 min/image). Presets dans `gui/ressources/session_configs.json`.
  - **Intervalle constant** : durée fixe par image (30 s, 1/3/5/10/20 min).
  - Liste d’images construite à partir des images filtrées (par tags), mélangée aléatoirement.
  - Fenêtre de session : plein écran ou « fenêtre toujours au premier plan » (depuis Session Settings).
  - Décompte par image en haut à droite ; barre du bas : Play/Pause, Précédent, Suivant ; Espace affiche/masque les contrôles, Échap ferme et revient à la fenêtre principale.
  - La fenêtre principale se cache au démarrage de la session et réapparaît à la fermeture de la fenêtre de session.
 → Résultat : Les utilisateurs peuvent lancer des sessions de dessin chronométrées à partir des images filtrées (Course ou intervalle constant), dans une fenêtre plein écran ou toujours au premier plan avec décompte et contrôles.
---
### ✅ Tâches (UI / tags) :
- Affichage des tags sur les images sélectionnées dans la grille
- Fenêtre de paramètres et améliorations du menu

- Ajout de l'affichage des tags dans ImageThumbnail quand l'image est sélectionnée
- Les tags sont affichés en bas des images sélectionnées avec leurs icônes
- Chaque chip de tag a un bouton de suppression (×) pour retirer le tag de toutes les images sélectionnées
- Les tags sont automatiquement rafraîchis quand ils sont mis à jour
- Ajout du widget TagChip pour afficher les tags dans les miniatures
- Ajout des styles pour les chips de tags dans les thèmes sombre et clair
- Le conteneur de tags utilise une mise en page en grille qui s'enroule automatiquement
- Optimisation de la mise en page des chips de tags : le texte est coupé (avec "...") quand l'espace est limité, préservant la visibilité de l'icône et du bouton de suppression
- L'icône et le bouton de suppression conservent leurs tailles minimales tandis que le texte s'adapte à l'espace disponible
- Suppression de l'obsolete EditTagDialog - toute l'édition de tags se fait maintenant directement dans l'interface principale
- Suppression des raccourcis clavier écrits dans les actions du menu File (interface plus propre)
- Ajout d'une fenêtre de paramètres accessible depuis le menu File
- La fenêtre de paramètres inclut la sélection du thème (Clair/Sombre)
- La fenêtre de paramètres inclut les paramètres de compression d'images :
  - Hauteur maximale pour les images importées (par défaut : 1080p, plage : 360p-4K)
  - Curseur de qualité de compression JPEG (par défaut : 75, plage : 30-100) avec descriptions de qualité
- Mise à jour de l'import d'images pour utiliser max_height au lieu de max_width pour un meilleur contrôle
- Qualité de compression par défaut changée de 85 à 75 pour un meilleur équilibre taille/qualité
 → Résultat : Les utilisateurs peuvent maintenant voir et gérer les tags directement sur les images sélectionnées dans la grille, avec une mise en page améliorée sur les miniatures de petite taille. Les paramètres sont maintenant centralisés dans une fenêtre dédiée pour une configuration plus facile.
---

## 2026-01-23
### ✅ Tâches :
- Mise à jour du dictionnaire de tags par défaut

- Remplacement des catégories et listes de tags de base
- Ajout des catégories dans l'autocomplétion de recherche
- Synchronisation des tags par défaut avec l'arbre des tags
- Marquage du libellé de catégorie "User Tags" comme non ajoutable
- Validation des tags existants avec animation de tremblement en cas d'erreur
- Support des dictionnaires de tags imbriqués dans le JSON par défaut
- Réduction des catégories tant que leur tag n'est pas sélectionné
- Remplacement de l'arbre par une grille de boutons catégories/sous-tags
- Grille de tags scrollable et sous-tags sur une seule colonne
- Filtrage OR par catégorie et AND sur les sous-tags
- Réorganisation de la grille : catégories en première colonne, sous-tags horizontalement à droite
 → Résultat : Les tags et catégories par défaut sont cohérents et recherchables dès le départ
---

## 2024-03-06
### ✅ Tâches :
- Configuration initiale du projet et structure de base
    - Création de la structure des répertoires (core, gui, data, utils)
    - Mise en place de l'environnement virtuel Python et des dépendances
    - Implémentation de la structure de base de la fenêtre GUI
    - Création des fichiers de modules initiaux et de la documentation
    → Résultat : La structure de base de l'application est en place avec une interface graphique fonctionnelle

### ✅ Tâches :
- Configuration du dépôt GitHub
    - Initialisation du dépôt Git
    - Configuration du .gitignore pour projet Python
    - Mise en place de la structure de documentation dans docs/
    - Création du README.md principal pour la visibilité du projet
    → Résultat : Le projet est maintenant correctement versionné et documenté sur GitHub

### ✅ Tâches :
- Référence Design UI
    - Ajout d'une image de référence pour le navigateur d'images
    - Création d'un document détaillé des spécifications UI
    - Documentation du système de design et des composants
    → Résultat : Lignes directrices UI clairement établies pour le développement

### ✅ Tâches :
- Implémentation du Gestionnaire de Paramètres
    - Création du template settings.json avec la configuration par défaut
    - Implémentation de la classe Settings avec validation et vérification de types
    - Ajout de tests unitaires complets pour la gestion des paramètres
    - Mise en place de la persistance des données avec stockage JSON
    → Résultat : Système de paramètres robuste prêt pour la configuration de l'application

## 2024-03-07
### ✅ Tâches:
    - Implémentation du Gestionnaire de Paramètres
        - Création du modèle settings.json avec la configuration par défaut
        - Implémentation du gestionnaire de paramètres dans core/settings.py avec fonctionnalités complètes
        - Ajout de tests unitaires complets dans tests/test_settings.py
        → Résultat: Système complet de gestion des paramètres avec persistance JSON, validation des types et couverture de tests 

### ✅ Tâches:
    - Implémentation des Utilitaires Système de Fichiers
        - Création de file_utils.py avec gestion des chemins et des répertoires
        - Implémentation des opérations sécurisées sur les fichiers et validation des répertoires
        - Ajout de tests unitaires complets avec pytest
        → Résultat: Utilitaires système de fichiers robustes prêts à être utilisés dans l'application 

### ✅ Tâches:
    - Implémentation de la Fenêtre GUI
        - Création de la fenêtre principale avec structure de menu (Fichier, Affichage, Aide)
        - Implémentation du changement de thème (Mode Clair/Sombre)
        - Ajout de la barre d'état et de la boîte de dialogue À propos
        - Création de tests unitaires complets
        → Résultat: Interface graphique de base prête avec support des thèmes

## 2024-03-26
### ✅ Tâches :
    - Système d'Import d'Images
        - Implémentation de la boîte de dialogue de sélection de fichiers
        - Ajout du support glisser-déposer pour les images
        - Création des utilitaires de traitement d'images
        → Résultat : Les utilisateurs peuvent maintenant importer des images via une boîte de dialogue ou par glisser-déposer, avec redimensionnement et optimisation automatiques
    
    - Base de Données d'Images
        - Conception et implémentation du stockage de métadonnées en JSON
        - Ajout du support des tags et des notes pour les images
        - Création des opérations CRUD pour la gestion des métadonnées
        → Résultat : Système complet de gestion des métadonnées pour les images importées

## 19 mars 2024
### ✅ Améliorations de la grille d'images

- Ajout de la fonctionnalité du slider de colonnes
  - Implémentation du contrôle slider (3-8 colonnes)
  - Ajout du redimensionnement dynamique de la grille
  - Optimisation des mises à jour de la disposition avec debouncing

- Optimisation de l'affichage des images
  - Implémentation des hauteurs de ligne dynamiques basées sur le contenu
  - Correction de la préservation du ratio d'aspect
  - Amélioration de la qualité de redimensionnement
  - Ajout du centrage correct des images

- Améliorations de l'interface
  - Implémentation du thème sombre pour la grille et les vignettes
  - Suppression des labels d'images pour une interface plus épurée
  - Ajout d'effets de survol sur les vignettes
  - Style des barres de défilement adapté au thème sombre

- Optimisations de performance
  - Amélioration du chargement et de la mise en cache des images
  - Optimisation des performances de défilement
  - Correction du chargement initial des images
  - Réduction des mises à jour de disposition inutiles

→ Résultat : Une grille d'images plus raffinée et réactive avec une meilleure cohérence visuelle et des performances améliorées

## 2024-03-27
### ✅ Tâches :
    - Optimisation de la grille d'images
        - Correction de la réactivité du curseur de colonnes
        - Amélioration de la mise en page et de la gestion des ratios d'aspect
        - Suppression du mécanisme de verrouillage complexe causant des blocages d'interface
        - Optimisation du timing des mises à jour de mise en page
        → Résultat : Grille d'images fluide et réactive avec des ratios d'aspect appropriés et sans blocage d'interface

## 2024-12-19
### ✅ Tâches :
    - Améliorations du système de sélection
        - Correction de la visibilité du rectangle de sélection lors du début du glissement sur les vignettes
        - Centralisation de toute la gestion des événements de souris dans ImageGrid (supprimé d'ImageThumbnail)
        - Amélioration du positionnement et du style de la bande élastique pour une meilleure visibilité
        - Amélioration du comportement Ctrl+glissement : retire toujours les vignettes de la sélection
        - Correction du centrage des images dans les vignettes pour un meilleur alignement visuel
        → Résultat : Système de sélection intuitif et réactif avec un retour visuel approprié

--- 