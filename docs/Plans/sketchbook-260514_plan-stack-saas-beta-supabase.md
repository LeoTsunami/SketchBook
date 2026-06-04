# SketchBook — Plan stack SaaS minimal (Supabase) & feuille de route

Document de travail pour **figer l’intention** et une **feuille de route** alignées sur les échanges récents (landing, téléchargements bureau, auth, marketplace de libs, coût quasi nul pour une beta ~10 personnes, puis montée en charge).  
Il **complète** sans remplacer [`sketchbook-260412_commercial-technique.md`](sketchbook-260412_commercial-technique.md) (vision large FastAPI + PostgreSQL) et [`sketchbook-260412_marche-prix-couts.md`](sketchbook-260412_marche-prix-couts.md) (coûts, pricing).

---

## 1. Volonté derrière ce stack

### 1.1 Objectif produit (première forme)

- **Landing** : présenter SketchBook, proposer le **téléchargement** Windows / macOS.
- **Client bureau** : conserver l’app **offline-first** existante, y ajouter une couche **compte** (Google + email) et un **catalogue** de bibliothèques d’images (marketplace).
- **Contenu** : au début **une lib gratuite** + **quelques libs payantes** (téléchargement de packs, typiquement **&lt; 1 Go par lib**, **&lt; 10 Go au total** pour la phase test).
- **Pilotage dev** : une stack **compréhensible dans Cursor**, peu de services à opérer, peu de code « glue » maison au début.

### 1.2 Pourquoi Supabase + statique + MoR (Lemon / Polar) ?

| Principe | Décision |
|----------|-----------|
| **Minimiser les pièces mobiles** | Un projet **Supabase** = Auth + base + stockage + règles d’accès, au lieu de monter tout de suite API + DB + fichiers séparément. |
| **Aller vite vers une beta testable** | **Site statique** pour la landing (pas de serveur à maintenir). |
| **Auth bureau sans OAuth maison lourd** | **Supabase Auth** (magic link email, Google) avec flux adaptés au desktop (navigateur / deep link selon implémentation). |
| **Paiements plus tard, simplement** | **Lemon Squeezy** ou **Polar** en **merchant of record** : checkout hébergé, webhooks pour créer les **droits** (`entitlements`) en base — à brancher quand on sort de la beta « gratuite ». |
| **Coût phase test (~10 personnes)** | Free tiers + binaires sur **GitHub Releases** + libs dans les quotas gratuits **si** le volume tient (voir pricing au moment du déploiement). |

### 1.3 Ce que ce plan ne fait pas (volontairement)

- Ne remplace pas une **due diligence juridique / fiscale** (TVA, MoR, micro-entreprise, etc.) — à valider avec un conseil au moment des premiers encaissements.
- Ne fige pas **FastAPI** comme cœur backend **jour 1** : la feuille de route large reste dans le doc commercial-technique ; ici on privilégie **BaaS** pour la v1 beta.
- Ne couvre pas encore **signature de code** Windows / **notarisation** Mac « grand public » (optionnel pour une beta interne ; recommandé avant diffusion large).

---

## 2. Stack retenue (vue d’ensemble)

```
┌─────────────────────────────────────────────────────────────────┐
│  Landing (statique) — Cloudflare Pages / GitHub Pages            │
│  · Pitch, captures, liens téléchargement Win/Mac                 │
│  · (Plus tard) liens checkout Lemon/Polar                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│  Supabase (un projet)                                            │
│  · Auth : email (magic link / OTP), Google OAuth                   │
│  · PostgreSQL : libraries, user_entitlements, métadonnées        │
│  · Storage : ZIP des libs (URLs signées) OU lien vers Releases   │
│  · Edge Functions (optionnel) : webhook achat → INSERT entitlement│
└────────────────────────────▲────────────────────────────────────┘
                             │ HTTPS + JWT
┌────────────────────────────┴────────────────────────────────────┐
│  SketchBook desktop (PySide6 / QtPy)                           │
│  · Module auth (session, refresh)                                │
│  · Module catalog / téléchargement / install local des libs      │
└─────────────────────────────────────────────────────────────────┘

Paiement (phase « lancer la machine ») : Lemon Squeezy ou Polar
```

**Fichiers lourds (ZIP)** : selon quotas, soit **Supabase Storage**, soit **GitHub Releases** pour la beta, avec **migration** vers stockage + CDN optimisé egress si la traction augmente.

---

## 3. Phases cibles

| Phase | Public | Paiement | Infra typique |
|-------|--------|----------|----------------|
| **A — Beta fermée** | ~10 testeurs | Non (droits manuels ou compte = accès) | Gratuit / minimal |
| **B — Landing publique** | Early adopters | Optionnel (early access) | Supabase + MoR |
| **C — Croissance** | Volume | Abonnements / packs | Pro Supabase, stockage egress optimisé (ex. R2), monitoring |

---

## 4. Feuille de route (ordre recommandé)

Les étapes sont **séquentielles** ; certaines peuvent se chevaucher une fois le socle Supabase créé.

### Étape 0 — Cadrage (0,5–1 j)

- [ ] Lister les **livrables** beta : quelles libs (gratuites / payantes simulées), formats (ZIP), OS cibles.
- [ ] Créer le **projet Supabase** (nom, région EU si clientèle EU).
- [ ] Décider où vivent les **binaires** (GitHub Releases recommandé pour la beta).

### Étape 1 — Données & contrats (1–2 j)

- [ ] Modèle SQL minimal : `libraries` (id, nom, description, `is_free`, `storage_key` ou URL, `version`, taille), `user_entitlements` (`user_id`, `library_id`, `source` : manual | purchase).
- [ ] Politiques **RLS** : lecture des libs publiques ; entitlements **uniquement** pour `auth.uid()`.
- [ ] (Option beta) Script SQL ou interface admin pour **accorder** une lib à un email testeur.

### Étape 2 — Auth dans l’app (3–7 j selon polish)

- [ ] Dépendance HTTP / client Supabase (ou REST direct avec gestion JWT).
- [ ] Écran **Login** : Google + email (magic link ou mot de passe si activé).
- [ ] Persistance session locale (fichier chiffré ou keychain — itération 2 si besoin).
- [ ] Flux OAuth desktop : navigateur + redirect (`localhost` ou schéma custom `sketchbook://`).

### Étape 3 — Catalogue & téléchargement (3–7 j)

- [ ] Appel API : liste des libs + **filtrage** selon entitlements.
- [ ] Téléchargement : **URL signée** Storage ou URL Release + vérif **hash** (optionnel mais utile).
- [ ] Installation dans le **répertoire user data** existant (`user_data`) + enregistrement « lib installée ».
- [ ] Intégration UI : entrée « Bibliothèques / Store » dans l’app (emplacement à trancher UX).

### Étape 4 — Landing (1–3 j)

- [ ] Repo ou dossier `web/` : page statique (Astro, ou HTML minimal).
- [ ] Déploiement **Cloudflare Pages** ou **GitHub Pages**.
- [ ] Liens vers **Releases** (Win / Mac) + courte doc « comment se connecter ».

### Étape 5 — Beta fermée (~10 personnes)

- [ ] Recrutement testeurs, **liste d’emails** alignée avec entitlements manuels.
- [ ] Collecte retours (formulaire, Discord, mail) — hors scope technique mais nécessaire au go/no-go.

### Étape 6 — « Lancer la machine » (après tests concluants)

- [ ] Compte **Lemon Squeezy** ou **Polar**, produits = libs payantes (ou bundle).
- [ ] **Edge Function** (ou serverless minimal) : webhook signé → `INSERT` dans `user_entitlements`.
- [ ] Passage **Supabase Pro** si quotas / SLA / support le justifient.
- [ ] Revue **juridique / compta** (CGU, confidentialité, TVA, statut auto-entreprise / société — voir docs marché).

### Étape 7 — Durcissement (parallèle ou juste après B)

- [ ] Signature Windows / notarisation Mac si distribution large.
- [ ] Observabilité (Sentry, logs), quotas anti-abus sur téléchargements.
- [ ] Stratégie **egress** si beaucoup de re-téléchargements (cache côté client, versioning des ZIP).

---

## 5. Critères de succès de la phase A (beta)

- Les **10 testeurs** peuvent **se connecter**, voir le **catalogue**, installer la **lib gratuite** et les libs pour lesquels ils ont un droit.
- **Aucun incident bloquant** (auth, téléchargement, corruption ZIP) sur **Windows et macOS** au moins sur une config « référence » chacune.
- Décision **go / no-go** documentée pour enchaîner phase B (landing publique + paiement).

---

## 6. Liens avec les autres plans

| Document | Rôle |
|----------|------|
| [`sketchbook-260412_1637.md`](sketchbook-260412_1637.md) | Vision produit, segments, concurrence. |
| [`sketchbook-260412_commercial-technique.md`](sketchbook-260412_commercial-technique.md) | Architecture cible long terme, implications légales/ops plus larges. |
| [`sketchbook-260412_marche-prix-couts.md`](sketchbook-260412_marche-prix-couts.md) | Pricing, coûts hors dev, scénarios budget. |
| **Ce document** | **Choix stack minimal** + **feuille de route** pour la première couche SaaS testable. |

---

## 7. Prochaine mise à jour utile

- Dater et ajuster **quotas Supabase** / **taille max GitHub Release** au moment du premier déploiement réel.
- Ajouter une **capture d’architecture** (schéma) si le repo accueille un module `cloud/` ou `sync/`.

---

*Document de travail — 2026-05-14. À réviser après la première beta fermée.*
