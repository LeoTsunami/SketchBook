# Journal des modifications

## 2026-04-10 (Passe cohérence couleur texte : libellés informatifs en blanc)
### ✅ Tâches :
- Uniformiser en blanc les textes informatifs clés de l'interface

- Mise à jour en blanc des libellés de la bibliothèque de tags (`Tags Library`, aide de sélection du parent).
- Mise à jour en blanc des libellés utilitaires de la top bar (`Sort`, `Columns`, compteur de colonnes).
- Mise à jour en blanc des métriques de la barre de statut (`Images: N` et résumé de sélection).
→ Résultat : Les textes informatifs de l'écran principal ont maintenant un contraste blanc cohérent.
---

## 2026-04-10 (Ajustement d'équilibre chrome : logo plus grand, ombre plus marquée, barre haute plus fine)
### ✅ Tâches :
- Ajuster la présence du logo et affiner l'épaisseur de la barre supérieure

- Augmentation de la taille du logo flottant pour renforcer la présence visuelle de la marque.
- Ajout d'une drop shadow marquée sur le logo flottant pour améliorer la profondeur et le détachement sur les fonds en dégradé.
- Réduction légère de la hauteur de la top bar pour garder une silhouette supérieure plus fine.
→ Résultat : Le header conserve un branding fort avec un logo mieux détaché, tout en retrouvant une barre supérieure plus légère.
---

## 2026-04-10 (Passe finale UX de la barre custom)
### ✅ Tâches :
- Finaliser l’ergonomie frameless et les proportions de la barre supérieure custom

- Amélioration du feedback de curseur de redimensionnement via l’event filter global (y compris au survol des widgets enfants proches des bords).
- Correction des glyphes minimize/maximize/restore (`-`, `□`, `❐`) pour se rapprocher des contrôles fenêtre standards.
- Ajustement des proportions : logo flottant légèrement réduit, barre supérieure augmentée en hauteur, et rail compact gauche un peu plus large.
→ Résultat : Le comportement frameless est plus naturel (resize plus lisible) et l’équilibre visuel de la top bar est plus proche du rendu final souhaité.
---

## 2026-04-10 (Affinage top bar : fenêtre frameless redimensionnable + boutons menus transparents)
### ✅ Tâches :
- Conserver le redimensionnement de la fenêtre custom frameless et affiner le style des boutons de menu supérieurs

- Ajout d'un hit-test sur les bords/coins et délégation native `startSystemResize(...)` pour garder le redimensionnement depuis les bordures.
- Mise à jour des boutons `File / View / Tools / Help` en fond transparent, avec survol blanc à très faible alpha.
- Augmentation de la hauteur de la barre supérieure custom pour améliorer lisibilité et respiration visuelle.
→ Résultat : La barre de titre custom garde le style souhaité tout en conservant un comportement de redimensionnement pratique.
---

## 2026-04-10 (Barre de fenêtre custom thémée avec menus app et contrôles système)
### ✅ Tâches :
- Remplacer la barre de titre native par une barre supérieure custom thémée incluant menus de l'app et boutons minimize/maximize/close

- Activation du mode fenêtre sans bordure native (frameless) et ajout des boutons de fenêtre custom (`_`, `[]`/restore, `X`) dans la barre supérieure existante.
- Conservation de `File / View / Tools / Help` sur la même ligne que les contrôles de grille, avec synchronisation d'état pour le bouton maximize/restore.
- Ajout de la gestion du drag et du double-clic sur le fond de la barre custom pour déplacer la fenêtre et basculer maximize/restore.
→ Résultat : L'application utilise maintenant une barre de fenêtre custom non blanche, cohérente avec le thème, avec menus et contrôles fenêtre sur la même ligne.
---

## 2026-04-10 (Nettoyage visuel sidebar tags : bibliothèque transparente + séparateur masqué)
### ✅ Tâches :
- Supprimer le fond de la zone scrollable de la bibliothèque de tags et rendre invisible le séparateur du splitter principal

- Mise à jour de `MainWindow` pour rendre `tags_scroll_area` transparent via un style ciblé par objet (`TagLibraryScrollArea`).
- Mise à jour du splitter horizontal principal avec un handle de largeur nulle et transparent (`MainImageSplitter`) pour masquer visuellement le séparateur.
- Comportement conservé, avec une séparation visuelle plus discrète entre la bibliothèque de tags et la galerie.
→ Résultat : La bibliothèque de tags se fond dans le fond du panneau, et le séparateur du splitter est visuellement invisible pour une interface plus propre.
---

## 2026-04-10 (Correctif environnement : Python stable pour PySide6)
### ✅ Tâches :
- Remplacer l'interpréteur instable du venv du projet et rétablir le chargement des bindings Qt

- Installation locale de Python 3.12.10 stable et recréation de `.venv` avec `py -3.12 -m venv .venv`.
- Réinstallation de toutes les dépendances depuis `requirements.txt` dans le nouvel environnement.
- Vérification que `PySide6` et `shiboken6` s'importent correctement, et que `main.py` s'importe sans erreur de binding Qt.
→ Résultat : Le projet utilise désormais un environnement virtuel stable (`.venv`) où les bindings Qt se chargent correctement, permettant un lancement normal depuis Cursor.
---

## 2026-04-10 (Expérience développeur : lancer main.py via le bouton Play Cursor)
### ✅ Tâches :
- Ajouter une configuration VS Code/Cursor de workspace pour lancer directement `main.py`

- Ajout de `.vscode/launch.json` avec un profil dédié `Python: Run main.py`.
- Ajout de `.vscode/settings.json` pour forcer l'interpréteur du workspace vers `.venv\\Scripts\\python.exe`.
- Configuration du lancement dans le terminal intégré avec la racine du workspace comme dossier courant.
→ Résultat : `main.py` peut maintenant être lancé directement depuis Cursor avec l'action Play/Run en utilisant le venv du projet.
---

## 2026-04-10 (Configuration d'environnement : environnement virtuel Python local)
### ✅ Tâches :
- Créer un environnement virtuel Python local et installer les dépendances du projet depuis `requirements.txt`

- Création de `.venv` à la racine du projet avec `py -3 -m venv .venv`.
- Mise à jour de `pip` dans l'environnement virtuel vers la dernière version disponible.
- Installation de toutes les dépendances listées dans `requirements.txt` (GUI, traitement d'image, validation, outils de dev et typage).
→ Résultat : Le projet dispose d'un environnement Python isolé prêt à l'emploi avec toutes les dépendances nécessaires installées.
---

## 2026-04-10 (Sidebar tags : contrôles flottants, panneau plus large, grille fluide)
### ✅ Tâches :
- Bouton filtres tags et logo flottants sur la grille ; rail tags replié à largeur 0 ; panneau ouvert plus large ; zone scroll en pleine hauteur ; **Start session** centré en bas ; resize fluide de la galerie conservé

- **Barre supérieure** : plus fine ; **logo flottant** au-dessus (hauteur indépendante) ; menus + contrôles grille. **Tags filters** un peu plus bas ; **survol** ouvre la bibliothèque de tags si elle est fermée.
- **Ajustements finaux** : boutons du menu du haut centrés verticalement, marge haute augmentée dans la bibliothèque de tags pour ne pas passer sous le logo flottant, repli automatique de la sidebar tags à la sortie de survol, et bouton **Tags filters** encore un peu plus bas.
- **Ajustement interaction** : bouton **Tags filters** en version verticale tout à gauche sous la zone logo, ouverture pilotée uniquement par survol (enter/mouse-move quand fermé), et légère marge haute ajoutée dans la top bar pour aérer les boutons.
- **Stabilité + layout** : correction du warning Qt `QFont::setPointSize <= 0` en clonant et bornant la taille de police des `TagChip` quand la police applicative est invalide ; conversion de **Tags filters** en rail vertical pleine hauteur collé au bord gauche (sous la zone logo).
- **Mise à jour interaction** : suppression du comportement flottant du bouton tags. La sidebar gauche a désormais deux états animés pilotés au survol : rail compact (bouton seul, largeur réduite) par défaut, puis bibliothèque de tags ouverte (bouton masqué) au survol.
- **Passe fluidité** : amélioration du repli avec des ticks de relayout coalescés plus fréquents, chemin de layout allégé pendant l’animation de sidebar, application différée du spacer compact uniquement en fin de repli, et préservation du ratio de scroll sans effets secondaires du scrollbar à chaque frame.
- **Rail tags** : largeur **0** quand fermé ; **~360** px à l’ouverture ; marge haute pour ne pas passer sous le bandeau logo ; logo plus grand.
- **Bibliothèque de tags** : la zone défilante prend l’espace vertical restant dans le panneau (stretch sur le `QScrollArea`, suppression de l’ancien stretch en bas).
- **Start session** : ancré au **centre bas** du viewport de la grille (au lieu du coin bas-droit).
- **Galerie** : `relayout_after_sidebar_step()` est appelé **uniquement à la fin** de l’animation de largeur du panneau tags (plus pendant l’animation).
- **Barre d’état** : nombre d’images et poids de la sélection à **droite** de la barre d’état (même bande que les messages). Panneau tags un peu moins large ; marge haute sous le bandeau logo ; logo plus grand.
- **Tests** : `tests/test_image_grid.py` pour `relayout_after_sidebar_step`.
 → Résultat : les filtres tags restent accessibles au même endroit ; le logo est en haut à gauche ; la bibliothèque de tags utilise mieux la hauteur ; le bouton de session est centré en bas.
---

## 2026-04-08 (Hiérarchie de tags : filtrage récursif des descendants)
### ✅ Tâches :
- Corriger le filtrage pour qu'une sous-catégorie parente inclue tous ses descendants imbriqués dans la grille d'images

- **Filtrage récursif** : Dans `MainWindow`, les filtres de catégories et de catégories label étendent désormais les tags sélectionnés avec tous leurs descendants récursifs avant le matching des tags image. Ainsi, sélectionner `Felin` inclut aussi les images taguées `Chat`, `Tiger`, `Lion`.
- **Matching OR des descendants pour une sous-catégorie sélectionnée** : chaque sous-catégorie sélectionnée crée désormais un groupe OR composé d'elle-même + descendants récursifs (au lieu d'un AND global sur tous les descendants). Cela corrige le cas "0 image" en cliquant un parent comme `Felin`.
- **Repères visuels de hiérarchie** : catégories et tags affichent désormais une flèche d'expand/collapse lorsqu'ils ont des enfants (`▶` replié, `▼` déplié). Ajout d'une coloration par profondeur pour mieux distinguer les niveaux imbriqués dans la grille.
- **Interactions tags cohérentes** : le clic simple est maintenant réservé au filtre et à l'expand/collapse. La sélection multiple dans la bibliothèque de tags se fait uniquement via modificateur+drag (`Ctrl` ou `Shift` + glisser), pour éviter les sélections accidentelles au clic.
- **UX de layout hiérarchique** : les tags enfants sont maintenant rendus systématiquement sur une nouvelle ligne sous leur parent sélectionné, avec position du parent stable dans l'ordre de la catégorie (plus de saut de sous-catégorie). Les lignes enfants ont aussi un encadrement visuel léger.
- **Nouveaux thèmes modernes** : ajout de trois thèmes avec dégradés (`Neon Night`, `Sunset Glass`, `Midnight Ocean`) et sélection possible depuis Settings et depuis le menu View > Theme.
- **Modernisation du style dark par défaut** : mise à jour du thème sombre de base avec un fond en dégradé violet/indigo et des contrôles translucides plus propres. La typographie par défaut de l'app passe à `Segoe UI` pour un rendu blanc plus simple et moderne.
- **Comportement de la sidebar tags** : suppression de la section haute devenue inutile dans le splitter vertical gauche et passage à une sidebar à largeur fixe, repliable/dépliable avec animation.
- **Sécurité anti-boucle** : Ajout d'une protection contre les cycles dans la traversal des descendants pour éviter une récursion infinie si une boucle parent/enfant invalide existe dans les placements utilisateur.
- **Tests** : Ajout de tests unitaires dans `tests/test_main_window.py` pour le cas attendu récursif, le cas limite d'un tag feuille, et le cas d'échec avec cycle.
 → Résultat : La hiérarchie de tags supporte des niveaux imbriqués illimités pour le filtrage, et cliquer une sous-catégorie parente remonte bien les images des sous-tags profonds.
---

## 2026-03-24 (Démarrer une session depuis l’image sélectionnée dans la grille)
### ✅ Tâches :
- Ajouter une action de menu contextuel pour démarrer une session depuis une image unique sélectionnée dans la grille

- **Comportement du menu contextuel** : Dans `ImageGrid`, le clic droit affiche désormais **« Start session from this image »** uniquement quand exactement une image est sélectionnée.
- **Comportement de démarrage de session** : Cette action ouvre la fenêtre Session Settings existante et démarre la session à partir de l’image sélectionnée ; les images précédentes dans l’ordre courant sont ignorées pour cette session.
- **Implémentation** : Ajout du signal `start_session_from_image_requested` dans `ImageGrid`, connecté dans `MainWindow` vers un nouveau handler qui réutilise `_on_session_settings_clicked(start_from_image_id=...)`. Ajout du helper `_slice_images_from_start()` pour conserver l’ordre tout en supprimant les images précédentes.
- **Tests** : Ajout de tests unitaires pour la logique de découpe (cas attendu, cas limite, cas d’échec) dans `tests/test_main_window.py`.
 → Résultat : Un clic droit sur une seule miniature permet de lancer une session qui commence exactement à cette image, puis continue dans l’ordre courant.
---

## 2026-03-14 (Bibliothèque de tags : défilement auto pendant le glisser de tags)
### ✅ Tâches :
- Défilement automatique de la bibliothèque de tags lorsque l’on glisse des tags près du haut ou du bas

- **Comportement** : Pendant le glisser d’un ou plusieurs tags utilisateur, si le curseur est à moins de 40 px du haut ou du bas de la zone défilable, la zone défile automatiquement (toutes les 120 ms) pour atteindre les tags au-dessus ou en dessous sans lâcher le glisser.
- **Implémentation** : flag `_tag_drag_in_progress` et timer `_tag_drag_scroll_timer` (QTimer) démarré avant `drag.exec_()` et arrêté dans un `finally` ; `_on_tag_drag_scroll_tick()` utilise la position globale du curseur et le rect du viewport pour ajuster la barre de défilement verticale.
 → Résultat : Glisser des tags pour les reparenter ou les appliquer aux images est plus simple lorsque la liste est longue ; la liste défile en approchant le curseur des bords.
---

## 2026-03-14 (Bibliothèque de tags : « Parent to tag... » depuis le menu contextuel)
### ✅ Tâches :
- Ajout de « Parent to tag... » au menu contextuel de la bibliothèque de tags (tags utilisateur uniquement)

- **Sélection multiple** : Ctrl+clic sur des tags utilisateur pour en sélectionner plusieurs ; clic droit sur l’un d’eux → « Parent to tag... » pour déplacer tous les tags sélectionnés sous un parent choisi.
- **Mode choix du parent** : Après « Parent to tag... », les tags à déplacer sont grisés. Une barre apparaît en haut de la bibliothèque : « Select parent tag: (none) » avec **OK** et **Cancel**. Cliquer sur un autre tag ou une catégorie le définit comme parent (le libellé se met à jour). **OK** applique le même placement que le glisser-déposer (les tags deviennent enfants de ce tag ou de cette catégorie) ; **Cancel** quitte sans modification.
- **Implémentation** : `_tag_library_selection` pour le Ctrl+clic, `_parent_select_mode` avec la barre et `_on_parent_select_ok` / `_on_parent_select_cancel` ; `eventFilter` sur les boutons de tags utilisateur pour le Ctrl+clic ; `_sync_tag_grid_state` grise les boutons dans `_tags_to_parent` en mode parent.
 → Résultat : On peut reparenter un ou plusieurs tags utilisateur sans glisser-déposer, en choisissant le parent puis en confirmant.
---

## 2026-02-11 (Visionneuse : crop avec grille des tiers et 4 points déplaçables)
### ✅ Tâches :
- Remplacer le crop par glisser-droite par un mode crop dédié : grille en tiers + Valider/Annuler

- **Nouveau flux de crop** : Cliquer sur **Crop** affiche une grille de règle des tiers sur l’image et le rectangle de crop couvre d’abord toute l’image. Quatre poignées (cercles blancs) aux coins permettent de redimensionner la zone. **Valider** applique le crop et enregistre sur le disque ; **Annuler** annule et quitte le mode crop.
- **Correctif** : Suppression de l’utilisation de `QRubberBand` dans la visionneuse (utilisé mais non importé, provoquant une NameError au clic droit). Le crop ne repose plus sur un glisser de rubber band.
- **Interne** : `ZoomGraphicsView` ne gère plus le crop ; l’état du mode crop, les éléments d’overlay (rectangle, lignes de grille, `CropHandleItem`) et Valider/Annuler sont gérés dans `ImageViewerWindow`. Les overlay sont retirés de la scène à la sortie du mode crop pour éviter les références invalides après `scene.clear()`.
 → Résultat : Le recadrage est plus clair, avec une grille règle des tiers et des boutons Valider/Annuler explicites.
---

## 2026-02-09 (Session : garder l'écran et le système actifs pendant la session)
### ✅ Tâches :
- Empêcher la mise en veille de l'écran et du système tant que la fenêtre de session est ouverte

- **Windows** : Utilise `SetThreadExecutionState` (ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED) via `utils/keep_awake.py` pour que l'écran et le PC restent actifs pendant la session (plein écran ou fenêtre). Comportement normal rétabli à la fermeture de la fenêtre de session.
- **Autres plateformes** : Aucune action (pas de dépendance) ; extension possible plus tard (macOS/Linux).
- **Tests** : `tests/test_keep_awake.py` pour l'idempotence de prevent_sleep/allow_sleep.
 → Résultat : L'ordinateur ne se met plus en veille pendant une session de dessin.
---

## 2026-02-10 (Grille : Session Course Random par défaut + miniatures plus nettes)
### ✅ Tâches :
- Mettre "Session Course Random" comme mode de tri par défaut et améliorer la qualité des miniatures dans la grille

- **Comportement de tri par défaut** : Au premier lancement, la grille d’images utilise désormais par défaut le mode de tri "Session Course Random", ce qui aligne immédiatement la galerie sur l’ordre pseudo-aléatoire des sessions Course. L’index de tri choisi par l’utilisateur est ensuite persisté dans les paramètres (`ui.grid.sort_index`) et restauré aux prochains lancements.
- **Cohérence de l’UI Shuffle** : La visibilité du bouton Shuffle est maintenant synchronisée avec l’état initial du combo de tri, et s’affiche donc correctement dès que "Session Course Random" est actif, y compris au démarrage.
- **Miniatures de meilleure qualité** : `ImageLoaderWorker` génère maintenant des pixmaps de vignettes en plus haute résolution en utilisant un facteur de suréchantillonnage plus élevé (au minimum 2.0x sur les écrans standard) avec `Qt.SmoothTransformation`. Les miniatures apparaissent nettement plus nettes dans la grille, en particulier après redimensionnement de la fenêtre et avec des configurations de colonnes larges.
 → Résultat : L’ordre aléatoire type "course" est utilisé par défaut à l’ouverture de l’application et les miniatures de la grille sont rendues avec une meilleure qualité visuelle.
---

## 2026-02-10 (Visionneuse : fit initial, navigation, rotation, crop)
### ✅ Tâches :
- Améliorer la fenêtre de visualisation d’image unique avec un meilleur fit initial et des outils de navigation

- **Fit au premier affichage** : La visionneuse reporte maintenant l’appel à `fitInView` via un petit `QTimer.singleShot(0, ...)`, ce qui permet, dès la toute première ouverture, d’utiliser la taille réelle de la fenêtre au lieu d’afficher une image minuscule qui ne se corrige qu’au second affichage.
- **Navigation Précédent/Suivant** : La visionneuse lit automatiquement la liste ordonnée courante d’images depuis l’`ImageGrid` (`all_images`) et expose des boutons **Previous** / **Next** pour parcourir la même séquence que dans la grille, en partant de l’image double-cliquée.
- **Rotation sur place** : Deux boutons, **Rotate ⟲** et **Rotate ⟳**, appellent `ImageManager.rotate_image()` pour faire pivoter l’image courante de 90° dans le sens horaire ou anti-horaire directement sur le disque, puis rafraîchir l’affichage et les métadonnées (largeur/hauteur).
- **Crop interactif + sauvegarde** : Un glisser avec le bouton droit dans la visionneuse dessine un rectangle de crop ; en cliquant sur **Crop**, le recadrage est appliqué au fichier sous-jacent via Pillow, les métadonnées (largeur, hauteur, taille de fichier) sont mises à jour, et l’image est rechargée pour visualiser immédiatement le nouveau cadrage dans SketchBook.
 → Résultat : La visionneuse ouvre les images à un niveau de zoom utile dès la première utilisation, permet de parcourir rapidement les images voisines et offre la rotation et le recadrage directement depuis l’application.
---

## 2026-02-09 (Session : Suiv./Préc. traitent Get ready et titres de phase comme des étapes)
### ✅ Tâches :
- Suivant et Précédent (et Gauche/Droite) traitent Get ready, titres de phase et images comme des étapes égales

- **Navigation par étapes unifiée** : Get ready, chaque titre de phase et chaque image sont des étapes. Suivant : Get ready → premier phase/image, titre de phase → image, image → prochain titre ou image. Précédent recule d'une étape (ex. retour au titre de phase, ou retour à Get ready depuis la première phase/titre).
- **Get ready est une étape** : Depuis la première phase ou la première image, Précédent peut ramener à l'écran Get ready (avec décompte 3-2-1). Depuis Get ready, Suivant continue vers le premier contenu.
 → Résultat : Même comportement pour chaque étape ; on peut passer ou revenir sur n'importe quel écran (Get ready, titres de phase, images) avec Suivant/Précédent.
---

## 2026-02-09 (Course : ajout de la phase Short pose 2 min 30, rééquilibrage warmup/gesture)
### ✅ Tâches :
- Ajout d'une étape intermédiaire entre 1 min et 5 min dans les presets Course

- **Nouvelle phase « Short pose »** : Insérée à 2 min 30 (150 s) entre Gesture (1 min) et Anatomy (5 min). Nom conforme à l’usage en modèle vivant pour les poses courtes.
- **Rééquilibrage des presets** : Tous les presets course (10–60 min) mis à jour : plus de place au warm-up et au gesture où possible ; le preset 10 min a maintenant 5 warm-up + 2 gesture + 1 short pose + 1 anatomy (~12 min au total pour inclure la nouvelle phase).
- **Sous-titre de phase** : Le slideshow affiche « 2 min 30 » pour les phases à 150 s (minutes non entières) dans l’overlay de titre de phase.
- **Docs et tests** : DOC_USER, DOC_DEV, docstring session_manager mis à jour ; assertions du test_session_manager mises à jour pour le nouveau nombre de slots 10 min et la durée 150.
 → Résultat : Les sessions Course enchaînent désormais 30 s → 1 min → 2 min 30 → 5 min → 10 min avec un accent plus marqué sur le warmup et le gesture.
---

## 2026-02-06 (ajout de l'option de tri Session Course Random)
### ✅ Tâches :
- Ajout de l'option de tri "Session Course Random" pour prévisualiser l'ordre de la session

- **Nouvelle option de tri** : Ajout de "Session Course Random" dans le combo box de tri de la grille. Cette option utilise le même algorithme de randomisation déterministe que les sessions Course, permettant aux utilisateurs de prévisualiser l'ordre exact des images qui seront utilisées dans une session avant de la démarrer.
- **Shuffle déterministe** : Implémentation de `_shuffle_images_for_session()` dans `core/image_db.py` et `_shuffle_image_ids_for_session()` dans `core/session_manager.py` qui utilisent une seed déterministe basée sur les IDs d'images triés. Cela garantit que le même ensemble d'images produit toujours le même ordre randomisé, correspondant entre la prévisualisation de la grille et la session réelle.
- **Cohérence des sessions** : Mise à jour de `build_course_run()` et de l'initialisation des sessions "Constant interval" pour utiliser le même shuffle déterministe, garantissant que l'ordre de prévisualisation dans la grille correspond exactement à l'ordre de la session.
 → Résultat : Les utilisateurs peuvent maintenant prévisualiser l'ordre de la session dans la grille avant de démarrer une session, facilitant la préparation aux sessions de dessin.
---

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