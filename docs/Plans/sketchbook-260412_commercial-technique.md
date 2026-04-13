# SketchBook — Feuille de route technique & commerciale

Ce document complète [`sketchbook-260412_1637.md`](sketchbook-260412_1637.md) (vision produit, concurrence, freemium, marché, cibles). Il décrit **ce qu’implique techniquement, juridiquement et opérationnellement** de viser une offre **commerciale** (abonnements, catalogue cloud, marketplace), en partant de **l’état actuel du code**.

---

## 1. État actuel du produit (constat code)

| Domaine | Réalité aujourd’hui |
|--------|----------------------|
| **Plateforme** | Application **bureau** Python 3.12+, **QtPy / PySide6**, point d’entrée `main.py`. |
| **Données utilisateur** | Dossier local (`Documents/SketchBook` par défaut, surcharge possible via `SKETCHBOOK_DATA_DIR` ou `.sketchbook_config.json`). |
| **Bibliothèque d’images** | Fichiers sur disque + métadonnées dans une **base JSON** (`ImageDatabase` dans `core/image_db.py`) : id, chemins, tags, dimensions, etc. Pas de serveur. |
| **Paramètres** | JSON via `core/settings.py` (thème, grille, session, etc.). |
| **Sessions** | Moteur de session, slideshow, minuteurs « Course » / « Constant », presets — le tout **100 % offline**. |
| **Comptes / réseau / paiement** | **Aucun** : cohérent avec `.cursor/PLANNING.md` (« pas de login ni dépendance réseau »). |
| **Tests** | Pytest sur modules clés (`tests/`). |
| **Packaging** | Non intégré au repo de façon industrialisée ; cible historique PyInstaller ou équivalent (à formaliser). |

**Synthèse :** le cœur produit est un **client riche offline-first** avec un modèle de données **fichier + JSON**. Passer au mode « commercial cloud + comptes + paiements » suppose **d’ajouter une couche services** et de **garder** ce socle local comme cache / mode dégradé.

---

## 2. Cible d’architecture (vue d’ensemble)

Pour aligner la vision (freemium, catalogue premium serveur, marketplace, forfaits écoles/entreprises, APIs type inspiration) avec une base maintenable :

```
┌─────────────────────────────────────────────────────────────────┐
│  Client SketchBook (Windows / macOS / Linux — plus tard mobile) │
│  · UI Qt existante                                                 │
│  · Cache images + métadonnées locale (JSON/SQLite)               │
│  · Module « sync / auth / store » (à créer)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (API REST ou GraphQL)
┌────────────────────────────▼────────────────────────────────────┐
│  Backend (à définir : FastAPI + PostgreSQL est un choix cohérent │
│  avec les conventions projet)                                     │
│  · Comptes, JWT / sessions, rôles (user / org / admin)           │
│  · Catalogue : métadonnées packs, tags, licences                 │
│  · Entitlements : abonnement, quotas téléchargement mensuel      │
│  · Marketplace : vendeurs, listings, commissions (phase tardive)│
│  · Paiements : Stripe Billing (ou équivalent) — webhooks         │
│  · Fichiers : stockage objet (S3, R2, Azure Blob, etc.)         │
└─────────────────────────────────────────────────────────────────┘
```

**Principe directeur :** ne pas remplacer brutalement le JSON local ; **synchroniser** ou **télécharger** des ressources serveur vers le cache local pour que l’app reste **utilisable hors ligne** sur le contenu déjà possédé (aligné avec la vision « offline + online pour marché / premium »).

---

## 3. Organisation de l’application (évolution du code)

### 3.1 Découpage module recommandé (sans tout réécrire)

| Module logique | Rôle | Lien avec l’existant |
|----------------|------|----------------------|
| `core/` (actuel) | Métier pur : tags, sessions, DB locale | Conserver ; ajouter des **ports** (interfaces) pour « source d’images » locale vs distante. |
| `gui/` | Interface | Ajouter écrans compte, boutique, état sync ; feature flags « online ». |
| `sync/` ou `online/` (nouveau) | Client API, auth, téléchargement résiliable, file d’attente offline | Isoler tout ce qui touche réseau pour tests et builds sans clés. |
| `licensing/` (nouveau) | Vérification droits locale (cache licence, expiration) | Évite de multiplier la logique dans l’UI. |

**Raison :** séparer **métier offline** et **couche réseau** permet de livrer encore des builds « offline only » et de tester le cœur sans backend.

### 3.2 Données locales : JSON → SQLite (option stratégique)

Aujourd’hui, `ImageDatabase` est un **gros JSON** avec sauvegarde debouncée et backup `.bak`. Pour des bibliothèques plus grosses et une sync incrémentale :

- **Court terme :** garder JSON pour la simplicité.
- **Moyen terme :** migrer vers **SQLite** (ou SQLModel) pour requêtes, index tags, delta sync — surtout si le catalogue distant devient volumineux.

Prévoir une **migration** scriptée et des tests (déjà une culture de tests dans le projet).

---

## 4. Base de données « en ligne » (serveur)

### 4.1 Modèle conceptuel minimal

- **Utilisateur** : email, hash mot de passe ou OAuth (Google, etc.), préférences.
- **Organisation** (B2B) : école / studio, sièges, facturation.
- **Produit catalogue** : packs d’images ou abonnement « bibliothèque » ; métadonnées (tags, résolution, licence).
- **Achat / abonnement** : lien vers **Stripe Customer / Subscription / Invoice** ; état miroir en base pour requêtes rapides.
- **Quota** : ex. N téléchargements / mois selon palier (comme évoqué dans la vision).
- **Téléchargements** : journal (audit, support, fraude légère).

### 4.2 Fichiers médias

- Stockage **objet** + URLs signées à durée courte pour téléchargement.
- **Checksum** (SHA-256) pour reprise et dédup côté client.

### 4.3 APIs « inspiration » / Pinterest

- Toute intégration tierce impose **respect des conditions d’utilisation** et souvent **API keys** ; prévoir un service dédié côté backend pour ne pas exposer de secrets dans le client packagé.

---

## 5. Utilisateurs, authentification, autorisation

| Sujet | Approche pragmatique |
|-------|----------------------|
| **Auth** | Email + mot de passe (argon2/bcrypt) et/ou **OAuth** ; tokens **JWT** court + refresh, ou session serveur. |
| **Sessions client** | Stockage sécurisé du refresh token (Keychain macOS, Credential Manager Windows, secret Linux). |
| **Rôles** | `user`, `org_admin`, `vendor` (marketplace), `admin`. |
| **Multi-poste** | Compte unique ; limiter simultané si abonnement individuel (policy produit). |

Le code actuel n’a **aucune** de ces briques : tout est à construire côté serveur + léger client dans l’app Qt.

---

## 6. Paiements et monétisation

### 6.1 Paiement récurrent et paliers

- **Stripe Billing** (ou Paddle, Lemon Squeezy selon juridiction et frais) pour **abonnements** et **factures** B2B.
- Webhooks : `customer.subscription.updated`, `invoice.paid`, etc. → mise à jour des **entitlements** en base.

### 6.2 Marketplace (phase ultérieure)

- Paiement **split** ou versement vendeurs (Stripe Connect classique).
- **KYC** vendeurs, **politique de remboursement**, **commission** : charge opérationnelle non triviale — à lancer **après** catalogue propriétaire stable.

### 6.3 Freemium dans le client

- **Feature flags** : limite nombre d’images locales importées, packs inclus, ou accès serveur bridé — décidé en produit ; le client lit un **profil licence** depuis l’API.

---

## 7. Packaging et distribution commerciale

| Étape | Contenu |
|-------|---------|
| **Build** | PyInstaller / cx_Freeze / Briefcase — un pipeline CI (GitHub Actions, etc.) par OS. |
| **Signatures** | **Windows** : Authenticode ; **macOS** : notarisation Apple ; indispensable pour limiter alertes sécurité. |
| **Mises à jour** | Sparkle (macOS), winsparkle ou équivalent, ou mise à jour in-app via paquets signés ; à planifier tôt. |
| **Canaux** | Site propre, Microsoft Store / Mac App Store (contraintes supplémentaires), ou les deux. |
| **Secrets** | Aucune clé API en dur ; configuration runtime ou OAuth. |

---

## 8. Légal et conformité

> Ceci n’est pas un avis juridique ; faire valider par un professionnel selon pays et modèle économique.

| Thème | Points à couvrir |
|-------|------------------|
| **CGU / CGV** | Usage du logiciel, du catalogue, limitations de licence, résiliation. |
| **Vie privée** | RGPD (UE) si utilisateurs UE : base légale, durée conservation, droits accès/suppression, DPA avec sous-traitants (hébergeur, Stripe). |
| **Cookies / analytics** | Si site web ou télémétrie : bandeau / consentement selon juridiction. |
| **Propriété intellectuelle** | Licence claire sur les **images** (création propriétaire, partenaires, utilisateurs marketplace) ; interdits de revente non autorisée. |
| **Contenu utilisateur** | Si un jour « boards » ou partage : modération, signalement, DMCA ou équivalent. |
| **Mineurs** | Si ciblage écoles : conformité scolaire et données d’élèves (souvent régime renforcé). |

---

## 9. Marketing et go-to-market (aligné vision)

| Cible (vision) | Implication |
|----------------|-------------|
| **Écoles d’art / 3D / communication** | Offre **multi-licences**, facturation, contact sales, éventuellement SSO (phase 2). |
| **Créateurs de contenu** | Programme ambassadeurs, démos courtes, assets visuels ; présence YouTube / Instagram / ArtStation. |
| **Différenciation** | Timing type cours de modèle vivant + **tags** + **offline** + (plus tard) inspiration IA — message simple. |

La **base propriétaire** au départ réduit la dépendance aux vendeurs tiers et clarifie la propriété des contenus pour la communication.

---

## 10. Phases de mise en œuvre suggérées

1. **Produit desktop mature** : stabilité, export/backup, éventuellement analytics locales (déjà en backlog `TASKS.md`).
2. **Backend minimal** : comptes + catalogue lecture seule + téléchargement pack « premium » + Stripe sur une offre simple.
3. **Abonnements + quotas** : synchronisation état licence, limites mensuelles.
4. **Organisations B2B** : sièges, facturation, admin.
5. **Marketplace** : vendeurs, modération, split paiements — **après** traction et cadre légal solide.

---

## 11. Risques et arbitrages

| Risque | Mitigation |
|--------|------------|
| Complexité **sync** client/serveur | Commencer par **téléchargement de packs** plutôt que sync temps réel partout. |
| **Coût stockage / bande passante** | CDN, mise en cache agressive côté client, packs différentiels. |
| **Fraude / partage de comptes** | Rate limiting, empreintes machine discrètes (transparence RGPD), pas de sur-collecte. |
| **Dépendance à un fournisseur** | Abstraction « PaymentProvider » / « BlobStorage » dans le backend. |

---

## 12. Cohérence avec `PLANNING.md`

Le planning actuel insiste sur **offline, pas de réseau**. La direction commerciale **étend** ce périmètre : il faudra **mettre à jour** `PLANNING.md` quand l’équipe décide d’engager le développement « online » (pour éviter que les contributeurs et l’IA appliquent des règles contradictoires).

---

## 13. Références internes utiles

- Vision produit : [`sketchbook-260412_1637.md`](sketchbook-260412_1637.md)
- Architecture générale : [`.cursor/PLANNING.md`](../../.cursor/PLANNING.md)
- Suivi tâches : [`.cursor/TASKS.md`](../../.cursor/TASKS.md)
- Métadonnées images : `core/image_db.py`
- Données utilisateur : `core/user_data.py`

---

*Document rédigé pour cadrer un passage en mode commercial ; à affiner au fil des choix produit (prix, paliers, géographies, fonctionnalités v1 cloud).*
