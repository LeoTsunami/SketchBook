# Rapport : conservation expand/collapse au drop de tag

## Objectif
Lors d’un drop d’un tag sur une catégorie ou sous-catégorie, la structure de visibilité (expand/collapse) doit rester identique : aucune catégorie ou sous-catégorie ne doit changer d’état au drop.

## Classes Qt utilisées (référence doc / Stack Overflow)

### QScrollArea
- **setWidgetResizable(True)** : le widget contenu est redimensionné pour remplir le viewport. La taille du widget est donc imposée par le viewport, pas par le contenu.
- Conséquence : avec `setWidgetResizable(True)`, le layout du contenu a une taille fixe (celle du viewport). Les lignes se partagent cette hauteur. Si une ligne a un `sizeHint()` / minimum à 0 (conteneur avec tous les enfants cachés), le layout peut lui attribuer 0 et ne pas recalculer après `setVisible(True)`.
- Référence : [QScrollArea with dynamically changing contents](https://stackoverflow.com/questions/21253755/qscrollarea-with-dynamically-changing-contents).

### QGridLayout
- **invalidate()** : marque le layout comme invalide (géométrie à recalculer).
- **activate()** : recalcule la géométrie. À appeler après `invalidate()` pour que le recalcul ait lieu.
- **setSizeConstraint(QLayout.SetFixedSize)** : le layout ne prend que la place nécessaire (taille = sizeHint). Utile pour que le widget contenu d’une scroll area signale sa “vraie” taille quand le contenu change.
- **setSizeConstraint(QLayout.SetMinimumSize)** : le layout respecte au moins la taille minimum de son contenu.
- Référence : [Resize QLayout to the minimum after widget size changes](https://stackoverflow.com/questions/14980620/resize-qlayout-to-the-minimum-after-widget-size-changes), [QTBUG-66151](https://bugreports.qt.io/) (layouts imbriqués).

### Comportement des layouts imbriqués
- Quand des enfants passent de cachés à visibles après un rebuild complet, Qt ne recalcule pas toujours la géométrie des layouts imbriqués (QGridLayout → conteneur → QGridLayout).
- Pistes documentées : `invalidate()` + `activate()` sur les layouts concernés ; parfois `hide()` puis `show()` sur le widget contenu pour forcer la scroll area à relayout.

---

## Flux actuel avant / après le drop

### Avant le drop (état en mémoire)
- **`_active_categories`** : catégories “ouvertes” (bouton actif + sous-tags visibles).
- **`_active_subtags`** : pour chaque catégorie, ensemble des sous-tags “sélectionnés” (filtre) et des sous-tags dont la ligne enfant est dépliée.
- L’UI reflète cet état (boutons actifs, `setVisible` sur les tag buttons, layout des conteneurs).

### Au drop (`_on_tag_grid_drop`)
1. **Highlight** : `_set_tag_grid_drop_highlight(None)`.
2. **Timer hover** : `_tag_grid_hover_expand_cancel()`.
3. **Validation** : MIME, tag utilisateur, cible (category ou tag), `role`, `key`.
4. **Config** : `user_tags_config.save_config(placements, ...)` (reparent en disque).
5. **Sauvegarde état** :  
   `saved_categories = set(self._active_categories)`,  
   `saved_subtags = {k: set(v) for k, v in self._active_subtags.items()}`.
6. **Deferred** : `QTimer.singleShot(0, _do_tag_grid_rebuild)`.

### Dans le deferred (`_do_tag_grid_rebuild`)
1. **Config** : `self._user_tags_config = user_tags_config.load_config()`.
2. **Reconstruction complète** : `self._load_tags_into_grid(skip_sync=True)`.

#### Ce que fait `_load_tags_into_grid(skip_sync=True)`
- **Détruit tout** : `while self.tags_grid_layout.count(): item = takeAt(0); item.widget().deleteLater()`.
- Réinitialise : `_category_buttons`, `_subcategory_buttons`, `_subcategory_containers`, `_subcategory_tag_order`, etc.
- **Ne touche pas** à `_active_categories` ni `_active_subtags`.
- Pour chaque catégorie (sauf label) :
  - Crée un `category_button` et un `tag_container` (QWidget avec QGridLayout).
  - Pour chaque sous-tag : crée un `tag_button`, l’ajoute au layout du conteneur, et fait **`tag_button.setVisible(is_label_category)`** → pour Animal/Human/etc. **tous les boutons sont créés cachés** (`False`).
  - Ajoute le conteneur à la grille : `tags_grid_layout.addWidget(tag_container, row+1, 0, 1, max_cols)`.
- **setRowStretch(max_row+1, 1)** sur la dernière ligne.
- **N’appelle pas** `_sync_tag_grid_state()` (skip_sync=True).

Conséquence : après `_load_tags_into_grid`, tous les conteneurs de catégories non-label ont tous leurs boutons **cachés**. Leur `sizeHint()` / hauteur minimum est donc 0. Au premier calcul de layout (implicite ou lors du prochain paint), la grille peut attribuer une hauteur 0 à ces lignes et ne pas mettre à jour après les futurs `setVisible(True)`.

3. **Restauration état** :  
   `self._active_categories = saved_categories`,  
   `self._active_subtags = saved_subtags`.
4. **Cible du drop** : ajout de `key` (et catégorie si role tag) dans `_active_categories` / `_active_subtags`.
5. **Sync UI** : `_sync_tag_grid_state()`.

#### Ce que fait `_sync_tag_grid_state()`
- Pour chaque catégorie : `is_active = category in self._active_categories`, `_set_button_active(button, is_active)`.
- Pour chaque tag button :  
  `tag_button.setVisible(is_active and ...)` ou `setVisible(is_active)` selon `parent_tag`.
- **Réorganisation des conteneurs** : pour chaque catégorie, `layout.takeAt(0)` sur le layout du conteneur, puis `layout.addWidget(btn, ...)` pour les boutons **déjà visibles** (`if btn.isVisible()`). Donc les boutons qu’on vient de rendre visibles sont bien ajoutés au layout du conteneur.
- À la fin : `invalidate()` / `activate()` sur chaque layout de conteneur, puis sur `tags_grid_layout`, puis `updateGeometry()`, `adjustSize()`, `update()` sur le conteneur et le viewport.

Malgré cela, l’UI reste “collapsed” : les données sont correctes (confirmé par les logs), mais l’affichage ne suit pas.

### Après le drop (deferred une seconde fois)
- `QTimer.singleShot(0, _force_layout_update)` : refait invalidate/activate, `adjustSize()`, puis **`tags_grid_container.setVisible(False)` puis `setVisible(True)`** pour forcer un relayout.

---

## Comparaison avec le comportement Qt attendu

| Élément | Comportement attendu (doc Qt) | Code actuel | Problème possible |
|--------|-------------------------------|-------------|-------------------|
| Layout après changement de visibilité | Recalcul après `invalidate()` + `activate()`. | On appelle les deux sur les layouts internes et sur la grille. | Premier calcul de la grille peut avoir lieu **avant** `_sync_tag_grid_state()` (avec tous les boutons cachés), et la grille peut “figer” les hauteurs de lignes. |
| Taille du widget dans QScrollArea | Avec `setWidgetResizable(True)`, la taille est imposée par le viewport. | `setWidgetResizable(True)` sans contrainte de taille sur le layout. | Le layout du contenu a une taille fixe ; les lignes à sizeHint 0 peuvent rester à 0 si le recalcul n’est pas déclenché au bon moment. |
| Contrainte de taille du layout | `SetFixedSize` / `SetMinimumSize` pour que le layout reflète la taille du contenu. | Aucun `setSizeConstraint` sur `tags_grid_layout` ni sur les layouts des conteneurs. | Le layout ne force pas un sizeHint cohérent avec le contenu visible. |
| Ordre des opérations | Visibilité puis recalcul du layout. | On fait setVisible dans _sync_tag_grid_state puis invalidate/activate. | Possible que le premier layout pass soit fait avant que les visibilités soient appliquées (race avec le paint/layout de Qt). |

---

## Pistes de correction (alignées avec la doc Qt)

1. **Contrainte de taille sur la grille principale**  
   `tags_grid_layout.setSizeConstraint(QLayout.SetMinimumSize)` (ou `SetFixedSize`) pour que la grille signale au moins la taille minimum nécessaire. Avec `setWidgetResizable(True)`, cela peut quand même aider au calcul interne des hauteurs de lignes.

2. **Contrainte sur les layouts des conteneurs**  
   Pour chaque `tag_container_layout`, `setSizeConstraint(QLayout.SetFixedSize)` (ou `SetMinimumSize`) pour que la hauteur du conteneur reflète le contenu visible.

3. **Recalcul explicite après restauration de l’état**  
   S’assurer qu’aucun layout pass ne soit fait entre la fin de `_load_tags_into_grid` et l’appel à `_sync_tag_grid_state()`. Déjà le cas en synchrone ; le risque est un layout pass déclenché par Qt (paint, show, etc.) avant notre `_sync_tag_grid_state()`.

4. **Alternative : éviter le full rebuild au drop**  
   Au lieu de `_load_tags_into_grid()` au drop, mettre à jour uniquement les placements en config et déplacer le(s) widget(s) de tag d’un conteneur à l’autre (sans recréer toute la grille). Ainsi, aucun changement de visibilité ni de structure de layout : l’état expand/collapse reste naturellement inchangé. C’est une refactor plus lourde mais la plus robuste pour “rien ne doit changer au drop”.

---

## Modifications appliquées (après rapport)

1. **Import** : ajout de `QLayout` dans les imports QtWidgets.
2. **Grille principale** : `tags_grid_layout.setSizeConstraint(QLayout.SetMinimumSize)` après création, pour que le layout signale au moins la taille minimum du contenu visible.
3. **Layouts des conteneurs** : dans `_load_tags_into_grid`, pour chaque `tag_container_layout`, appel à `setSizeConstraint(QLayout.SetMinimumSize)` après création.
4. **QScrollArea** : `tags_scroll_area.setWidgetResizable(False)` au lieu de `True`. Avec `False`, la zone de scroll utilise le `sizeHint()` du widget contenu (donné par le layout) au lieu de le redimensionner au viewport ; les lignes étendues peuvent donc obtenir la bonne hauteur après recalcul du layout.
5. Les appels **invalidate/activate**, **updateGeometry**, **adjustSize** et le deferred **hide/show** sont conservés pour forcer le recalcul après `_sync_tag_grid_state`.

Si le collapse persiste, la suite prévue est une mise à jour minimale au drop (sans `_load_tags_into_grid`, uniquement déplacer les boutons de tag concernés entre conteneurs).
