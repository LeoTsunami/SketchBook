# SketchBook — Plan de réécriture complète en TypeScript

Document de travail pour **cadrer une reconstruction** de SketchBook en **TypeScript**, avec portabilité **desktop → web → mobile**, backend **Supabase**, et **marketplace** de bibliothèques d’images.

Il **complète** :

- [`sketchbook-260412_1637.md`](sketchbook-260412_1637.md) — vision produit
- [`sketchbook-260412_commercial-technique.md`](sketchbook-260412_commercial-technique.md) — implications commerciales et architecture cible
- [`sketchbook-260514_plan-stack-saas-beta-supabase.md`](sketchbook-260514_plan-stack-saas-beta-supabase.md) — beta SaaS minimale (peut coexister en parallèle sur l’app Python)

**Statut :** réflexion / décision — **ne remplace pas** le code Python tant qu’une phase 0 de validation n’est pas actée.

---

## 1. Pourquoi envisager une réécriture

### 1.1 Limites du socle actuel (Python + Qt)

| Constat (code actuel) | Impact long terme |
|----------------------|-------------------|
| `gui/main_window.py` monolithique (~5k+ lignes) | Maintenance difficile, onboarding lent |
| UI 100 % Qt (`PySide6` / `QtPy`) | Pas de portage web / mobile sans réécriture UI |
| Données locales JSON (`core/image_db.py`) | OK pour MVP ; limite sync / grosses libs |
| Offline-first mature, tests pytest solides | **À préserver** comme référence comportementale |
| Aucun auth / cloud / paiement | Couche à ajouter de toute façon |

### 1.2 Ce qu’on cherche avec TypeScript

- **Une base de code partagée** entre desktop, web (landing + store), et plus tard mobile.
- **Supabase** comme backend unique (Auth, PostgreSQL, Storage, Edge Functions).
- **Réactivité UI** moderne (grille virtualisée, tag library, drag & drop).
- **Offline-first** conservé : cache local + sync / téléchargement de packs.
- **Écosystème SaaS** (paiements, webhooks, admin marché) sans glue maison excessive.

### 1.3 Ce que ce plan n’est pas

- Un ordre de « tout jeter demain » : une **stratégie de coexistence** est décrite (§8).
- Un choix figé React vs Svelte : **décision ouverte** (§4.2).
- Un avis juridique ou un budget détaillé (voir [`sketchbook-260412_marche-prix-couts.md`](sketchbook-260412_marche-prix-couts.md)).

---

## 2. Stack cible (proposition)

### 2.1 Vue d’ensemble

```
┌─────────────────────────────────────────────────────────────────────────┐
│  apps/web          Landing, compte, catalogue marché, checkout (MoR)     │
│  (Vite ou Next.js)                                                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼─────────────────────────────────────────┐
│  Supabase                                                                  │
│  · Auth (Google, email)   · PostgreSQL   · Storage   · Edge Functions (TS) │
└───────────────────────────────▲─────────────────────────────────────────┘
                                │ JWT + REST / Realtime (optionnel)
┌───────────────────────────────┴─────────────────────────────────────────┐
│  apps/desktop   Tauri 2 + React (ou Svelte)                              │
│  · Session player, grille, tag library, import, sync packs               │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ phase 2
┌───────────────────────────────▼─────────────────────────────────────────┐
│  apps/mobile    Expo (React Native) — sessions + catalogue simplifié     │
└─────────────────────────────────────────────────────────────────────────┘

        packages/core      Métier pur (tags, filtres, sessions, entitlements)
        packages/db        SQLite locale, migrations, modèles
        packages/supabase  Client typé, queries, auth helpers
        packages/ui        Composants partagés (si React partout)
```

### 2.2 Choix techniques recommandés

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Langage | **TypeScript** (strict) | UI, métier, Edge Functions, tooling |
| Monorepo | **pnpm** + **Turborepo** | Apps + packages, CI unifiée |
| Desktop | **Tauri 2** | Win / Mac / Linux, accès fichiers, petits binaires |
| Web | **Vite** (SPA) ou **Next.js** (SSR landing + SEO) | Store, compte, docs |
| Mobile (phase 2) | **Expo** | iOS / Android / tablette |
| UI desktop/web | **React 19** + **Tailwind** | Ou **SvelteKit** si perf UI prioritaire |
| État serveur | **TanStack Query** | Cache, retry, offline-friendly |
| État UI local | **Zustand** ou **Jotai** | Sélection tags, panneaux, session en cours |
| Listes / grilles | **@tanstack/react-virtual** | Grille d’images performante |
| DnD | **@dnd-kit** | Tags, réorganisation (remplace Qt DnD) |
| DB locale | **SQLite** via **Drizzle ORM** | Remplace JSON `ImageDatabase` |
| Validation | **Zod** | Schémas partagés API ↔ client |
| Tests | **Vitest** + **Playwright** | Unitaires + E2E desktop/web |
| Rust (optionnel) | Plugins **Tauri** | Hash fichiers, scan dossiers, thumbnails natifs |
| Paiements | **Lemon Squeezy** / **Polar** → webhooks → Edge Functions | Entitlements en base |
| CI | GitHub Actions | Lint, test, build Tauri, deploy web |

### 2.3 Décisions encore ouvertes

| Sujet | Option A | Option B | Critère de tranchage |
|-------|----------|----------|---------------------|
| UI framework | React | Svelte | Perf perçue tag library vs écosystème composants |
| Web framework | Vite SPA | Next.js | Besoin SEO landing / blog / docs |
| ORM local | Drizzle | Kysely | Préférence équipe + migrations |
| Partage UI mobile | Expo seul | Expo + composants `ui` partiels | Parité fonctionnelle tablette |

---

## 3. Principes d’architecture

### 3.1 Règles non négociables (héritées du produit actuel)

1. **Offline-first** : toute image / pack déjà installé reste utilisable sans réseau.
2. **Séparation métier / UI** : `packages/core` ne dépend d’aucun framework UI.
3. **Source d’images abstraite** : interface `ImageLibrarySource` (locale, pack cloud, hybride).
4. **Comportement de référence** : les tests Python existants servent de **spécification** pour les tests TS.
5. **Pas de secrets dans le client** : clés paiement / admin uniquement côté Edge Functions.

### 3.2 Modèle de données locale (cible)

Migration conceptuelle depuis `ImageMetadata` + `user_tags_config.json` :

| Entité | Stockage | Notes |
|--------|----------|-------|
| `images` | SQLite | id, paths, dimensions, hash, import_date |
| `image_tags` | SQLite | relation N-N |
| `tags` | SQLite | nom, taxonomie, parent, shelf |
| `tag_placements` | SQLite | équivalent `placements` user tags |
| `installed_libraries` | SQLite | packs téléchargés, version, chemin racine |
| `settings` | SQLite ou fichier JSON | thème, grille, session defaults |
| `sync_state` | SQLite | dernière sync, entitlements en cache |

### 3.3 Modèle cloud (Supabase — aligné plan SaaS)

Tables minimales (voir plan Supabase existant) :

- `libraries` — catalogue (gratuit / payant, version, taille, `storage_key`)
- `user_entitlements` — droits par utilisateur
- `purchases` — miroir webhooks MoR (phase paiement)
- `vendors` / `listings` — marketplace phase tardive

---

## 4. Cartographie Python → TypeScript

### 4.1 `core/` — priorité haute (migrer en premier)

| Module Python actuel | Package TS cible | Complexité | Notes |
|---------------------|------------------|------------|-------|
| `core/image_db.py` | `packages/db` + `packages/core/images` | Haute | JSON → SQLite ; conserver sémantique filtres / tri |
| `core/image_manager.py` | `packages/core/images` | Moyenne | Orchestration import, chemins |
| `core/session_manager.py` | `packages/core/session` | Moyenne | Modes Course / Constant, presets |
| `core/settings.py` | `packages/core/settings` | Faible | Schéma Zod |
| `core/user_data.py` | `packages/core/paths` | Faible | Chemins user data par OS (Tauri APIs) |
| `core/user_tags_config.py` | `packages/core/tags` | Moyenne | Taxonomie, shelves, merge custom |
| `core/config_backup.py` | `packages/core/backup` | Faible | Export / import config |

### 4.2 `gui/` — réécriture UI (par ordre produit)

| Zone fonctionnelle | Fichiers Python de référence | Composant TS cible | Priorité MVP |
|-------------------|------------------------------|-------------------|--------------|
| Grille d’images | `image_grid.py`, `image_thumbnail.py` | `ImageGrid`, virtualisation | P0 |
| Session / slideshow | `slideshow_window.py`, `session_timer.py` | `SessionPlayer` | P0 |
| Filtres AND/OR | `tag_widgets.py`, `tag_manager.py` | `TagFilterBar` | P0 |
| Tag library | `main_window.py` (partie tags), `tag_panel_overlay.py` | `TagLibraryPanel` | P1 |
| Import images | `import_dialog.py`, workers import | `ImportWizard` + workers Tauri | P1 |
| Viewer plein écran | `image_viewer_window.py` | `ImageViewer` | P2 |
| Settings | `settings_dialog.py`, `session_settings_dialog.py` | `SettingsModal` | P2 |
| Chrome fenêtre | `window_chrome.py` | Tauri decorations / custom titlebar | P2 |
| Thèmes | `styles/*.qss`, `theme_qss_utils.py` | Tailwind + CSS variables | P1 |

### 4.3 Tests — à réimplémenter comme contrat

Les tests pytest actuels (`tests/test_*.py`) définissent le comportement attendu. Priorité de portage :

1. `test_image_db.py`, `test_session_manager.py`, `test_tag_shelves.py`, `test_user_tags_config.py`
2. `test_image_grid*.py`, `test_tag_manager.py`
3. E2E Playwright : démarrage app, lancer session, filtrer par tag

---

## 5. Phases de réécriture

### Phase 0 — Cadrage (1–2 semaines)

- [ ] Décision go / no-go réécriture (vs continuer Python + Supabase seulement)
- [ ] Trancher React vs Svelte, Vite vs Next.js
- [ ] Créer repo ou dossier `sketchbook-ts/` (monorepo vide)
- [ ] Rédiger **spec comportementale** : sessions, filtres tags, tri, offline
- [ ] Inventorier les **constantes UI** actuelles (timings session, colonnes grille, taxonomie tags)

**Livrable :** repo initial + CI qui build + 10 tests Vitest sur `packages/core`.

### Phase 1 — Noyau métier (3–5 semaines)

- [ ] `packages/core` : tags, filtres AND/OR, hiérarchie catégories
- [ ] `packages/db` : SQLite, migrations, import depuis JSON Python (outil one-shot)
- [ ] `packages/core/session` : Course, Constant, shuffle
- [ ] Port des tests unitaires critiques depuis pytest
- [ ] CLI dev `pnpm dev:core` pour tester sans UI

**Livrable :** même jeu d’images + tags → mêmes résultats de filtre / session qu’en Python (tests automatisés).

### Phase 2 — Desktop MVP (6–10 semaines)

- [ ] `apps/desktop` Tauri : shell, chemins user data, keep-awake
- [ ] Grille virtualisée + thumbnails (cache disque)
- [ ] Session player plein écran
- [ ] Barre filtres AND/OR basique
- [ ] Import dossier images
- [ ] Settings minimaux (colonnes, tri, thème)

**Livrable :** app desktop utilisable en **offline pur**, parité ~70 % avec Python sur le cœur session.

### Phase 3 — Tag library & UX avancée (4–6 semaines)

- [ ] Panneau tag library (overlay, recherche, multi-sélection)
- [ ] Drag & drop tags (réorganisation user tags)
- [ ] États visuels tags (repos, hover, selected, actif)
- [ ] Hiérarchie catégories / shelves

**Livrable :** parité ~90 % UX tags avec l’app Qt actuelle.

### Phase 4 — Supabase & catalogue (3–5 semaines)

- [ ] `packages/supabase` : auth desktop (OAuth + deep link / localhost)
- [ ] Liste bibliothèques + entitlements
- [ ] Téléchargement pack ZIP → installation locale
- [ ] Cache entitlements offline

**Livrable :** beta fermée alignée sur [`sketchbook-260514_plan-stack-saas-beta-supabase.md`](sketchbook-260514_plan-stack-saas-beta-supabase.md).

### Phase 5 — Web store & landing (2–4 semaines)

- [ ] `apps/web` : landing, login, catalogue, liens download desktop
- [ ] Checkout MoR (Lemon / Polar) + webhook Edge Function
- [ ] Pages légales (CGU, confidentialité)

**Livrable :** parcours web complet sans ouvrir l’app desktop.

### Phase 6 — Mobile (phase 2 produit, 8–12 semaines)

- [ ] `apps/mobile` Expo : auth, catalogue, session simplifiée
- [ ] Réutilisation `packages/core` + `packages/supabase`
- [ ] UI adaptée tactile (pas de copie 1:1 du desktop)

### Phase 7 — Décommission Python (progressif)

- [ ] Feature parity checklist signée
- [ ] Migration données utilisateur (outil import config JSON → SQLite TS)
- [ ] Gel du repo Python en maintenance critique seulement

---

## 6. Structure monorepo proposée

```
sketchbook/
├── apps/
│   ├── desktop/          # Tauri + React
│   │   ├── src/
│   │   └── src-tauri/    # Rust minimal (fs, hash, native)
│   ├── web/              # Vite ou Next.js
│   └── mobile/           # Expo (phase 2)
├── packages/
│   ├── core/             # tags, session, filters, entitlements logic
│   ├── db/               # Drizzle schema, migrations, repositories
│   ├── supabase/         # client, generated types, hooks
│   ├── ui/               # composants partagés (optionnel mobile)
│   └── config/           # eslint, tsconfig, tailwind preset
├── supabase/
│   ├── migrations/
│   └── functions/        # Edge Functions TypeScript
├── tooling/
│   └── migrate-from-python/  # scripts import JSON → SQLite
├── docs/
└── package.json
```

---

## 7. Risques et mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Double maintenance Python + TS longtemps | Haute | Élevé | Phase 0 go/no-go ; limiter scope MVP |
| Régression UX (tag library, perf grille) | Haute | Élevé | Tests E2E ; benchmarks grille vs Python |
| DnD / overlay moins fluide qu’en Qt | Moyenne | Moyen | Prototype tag library en phase 0 |
| Auth desktop OAuth fragile | Moyenne | Moyen | Suivre doc Supabase PKCE ; tester Win+Mac tôt |
| Coût temps sous-estimé | Haute | Élevé | MVP sans marketplace vendeurs |
| Tauri / WebView différences OS | Moyenne | Moyen | CI multi-OS dès phase 2 |

---

## 8. Stratégie de coexistence avec Python

Ordre recommandé pour **limiter le risque** :

```
1. Valider Supabase sur l’app Python (plan 260514)     ← business sans rewrite
2. Extraire spec + tests comme contrat                  ← pendant ou après beta
3. Démarrer packages/core TS en parallèle               ← pas de big bang
4. Desktop TS MVP offline                               ← première app « v2 »
5. Basculer nouveaux utilisateurs sur TS                ← quand checklist OK
```

**Ne pas** lancer la réécriture complète avant d’avoir :

- une beta auth + catalogue validée **ou**
- une preuve que Qt bloque réellement la roadmap mobile/web à court terme.

---

## 9. Critères de succès (definition of done v2)

### MVP desktop (fin phase 2–3)

- [ ] Import et navigation dans une bibliothèque locale 10k+ images sans freeze UI
- [ ] Sessions Course et Constant identiques en comportement au Python
- [ ] Filtres tags AND/OR + catégories hiérarchiques
- [ ] 100 % offline sur contenu local
- [ ] Tests unitaires `core` + 5 scénarios E2E Playwright verts
- [ ] Build signé Win + Mac (ou nightly unsigned pour beta)

### v2 cloud (fin phase 4–5)

- [ ] Login Google + email
- [ ] Téléchargement et installation d’au moins 1 pack cloud
- [ ] Entitlements respectés offline (cache)
- [ ] Landing + store web en production

---

## 10. Estimation d’effort (ordre de grandeur)

Hypothèse : **1–2 devs** à temps partiel, en réutilisant la spec Python.

| Phase | Durée indicative |
|-------|------------------|
| 0 Cadrage | 1–2 semaines |
| 1 Noyau métier | 3–5 semaines |
| 2 Desktop MVP | 6–10 semaines |
| 3 Tag library | 4–6 semaines |
| 4 Supabase | 3–5 semaines |
| 5 Web store | 2–4 semaines |
| **Total jusqu’à beta cloud** | **~5–9 mois** |
| 6 Mobile | +2–4 mois |

*À affiner après un spike technique de 1 semaine (grille + 1 session en Tauri).*

---

## 11. Spike technique recommandé (1 semaine)

Avant d’engager la réécriture complète :

1. Monorepo minimal + Tauri + React + Vitest
2. Grille 500 thumbnails avec virtualisation + scroll fluide
3. Timer session 30s / 1min / 2min30 sur 20 images
4. Lecture d’un export JSON `ImageDatabase` Python importé en SQLite
5. Mesure : FPS scroll, RAM, temps cold start

**Critère spike :** scroll grille ≥ 55 fps sur machine cible dev ; sinon revoir React vs Svelte ou cache thumbnails Rust.

---

## 12. Prochaines actions

- [ ] Relire ce plan et cocher **go / no-go / go partiel** (core TS seulement d’abord)
- [ ] Si go : créer le repo monorepo et le spike (§11)
- [ ] Mettre à jour `.cursor/PLANNING.md` quand la direction TS est actée
- [ ] Lier ce document depuis [`sketchbook-260412_commercial-technique.md`](sketchbook-260412_commercial-technique.md) §13

---

## 13. Références internes

| Ressource | Chemin |
|-----------|--------|
| DB locale actuelle | `core/image_db.py` |
| Sessions | `core/session_manager.py` |
| Tags / shelves | `core/user_tags_config.py`, `gui/tag_shelves.py` |
| UI principale | `gui/main_window.py` |
| Tests comportement | `tests/` |
| Styles | `gui/styles/` |

---

*Document de travail — 2026-06-04. À réviser après le spike technique et/ou la beta Supabase sur Python.*
