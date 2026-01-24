# Journal des modifications

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