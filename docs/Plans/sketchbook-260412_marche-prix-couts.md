# SketchBook — Étude de marché, réflexion tarifaire, coûts de mise en route (hors développement)

Document de travail pour compléter la vision ([`sketchbook-260412_1637.md`](sketchbook-260412_1637.md)) et la feuille de route technique ([`sketchbook-260412_commercial-technique.md`](sketchbook-260412_commercial-technique.md)).  
**Périmètre :** analyse commerciale et **estimation des charges hors développement logiciel** (juridique, infra, outils, distribution, marketing minimal). Les montants sont des **ordres de grandeur** en **euros (€)** ; à ajuster selon pays d’immatriculation, volume, et devis réels.

---

## 1. Étude de marché (synthèse)

### 1.1 Proposition de valeur SketchBook (rappel)

- Entraînement au **dessin d’après modèle** avec bibliothèque **taguée**, **sessions chronométrées** (Course / Constant), usage **local** et **cloud** visé.
- Différenciation possible : **offline-first**, **performance** (grille, sessions), **organisation par tags** (vs simple galerie web), et plus tard **packs premium**, **B2B écoles**, **marketplace**.

### 1.2 Segments de clientèle

| Segment | Besoin principal | Sensibilité au prix | Cycle d’achat |
|--------|-------------------|---------------------|----------------|
| **Hobbyistes / étudiants** | Bibliothèque variée, simplicité | Forte — comparaison aux apps loisir / jeux | Court, impulsion |
| **Auteurs / freelances art** | Références fiables, gain de temps | Moyenne — ROI sur temps de recherche | Court à moyen |
| **Écoles / studios (B2B)** | Licences multiples, facturation, parfois offline | Faible si budget pédagogique | Long — devis, conformité |
| **Créateurs de contenu** | Visuel « pro », nouveautés | Moyenne — sponsor / revenus ads | Dépend de l’audience |

### 1.3 Paysage concurrentiel (indirect / direct)

Les références listées dans le plan initial ne sont pas toutes comparables (gratuit web, apps mobile, moodboard). Utile de classer :

| Type | Exemples (vision doc) | Modèle souvent observé | Implication pour SketchBook |
|------|------------------------|-------------------------|-----------------------------|
| **Sites de poses / timers web** | Line of Action, SketchDaily, timers Pinterest | Gratuit (pub / dons) | Ancre l’idée que « l’entraînement pose » peut être **gratuit** — le **premium** doit apporter catalogue curaté, offline, perf, packs, ou outils pro. |
| **Apps « références » mobile** | Artista, Drawing References (Play) | Freemium / achat in-app | Ancrage prix **quelques €/mois** ou **pack** sur les stores — comparable à loisir créatif. |
| **Moodboard / références bureau** | PureRef | Gratuit perso ; **business** souvent **licence / abonnement par siège** (tarifs **à vérifier** sur [pureref.com](https://www.pureref.com/)) | Ancrage **outil pro** : acceptable de facturer plus si valeur « studio / pipeline ». |
| **Banques d’images / stock** | Shutterstock, Adobe Stock, etc. | Abonnement ou crédits | Si SketchBook vend des **packs** ou **droits**, la perception prix est celle du **stock** (large gamme selon résolution et licence). |

**Conclusion marché :** le produit se situe à la croisée **outil de productivité créative** (comme un viewer / workflow) et **contenu média** (banques d’images). La **double ancre** (outil + contenu) permet un pricing plus riche qu’un simple timer web, à condition que la **qualité du catalogue** et la **licence** soient claires.

### 1.4 Forces, faiblesses, opportunités, risques (SWOT courte)

| | |
|---|--|
| **Forces** | Offline-first, sessions structurées, tags, desktop performant déjà avancé côté app. |
| **Faiblesses** | Pas encore d’écosystème cloud / compte ; coût de **production ou acquisition** d’un gros catalogue légal. |
| **Opportunités** | Niches **écoles d’art** et **studios** (packs + sièges) ; **marketplace** long terme si communauté. |
| **Risques** | Concurrence gratuite forte ; **sensibilité au prix** du segment étudiant ; **conformité** des images (droits modèle / propriété). |

---

## 2. Réflexion sur le prix des abonnements

### 2.1 Principes

1. **Ancrage psychologique** : les utilisateurs comparent à **Netflix**, **Adobe**, **une app App Store à 2,99 €/mois**, ou à **0 €** (sites de poses). Il faut **justifier** : volume de contenu, qualité, licence, offline, support, mises à jour.
2. **Coût variable réel** : stockage + bande passante + paiement + support + (éventuellement) **paiement aux créateurs** en marketplace. Le prix doit couvrir **marge brute** après frais de carte (souvent **~3 % + fixe** par transaction sur des schémas type Stripe — voir grille tarifaire officielle au moment du lancement).
3. **Freemium** (déjà dans la vision) : la version gratuite fixe l’ancrage « accessible » ; le **Pro** doit avoir **2–3 bénéfices évidents** (catalogue premium, quota de téléchargements, packs B2B, pas de pub si un jour pub il y a).

### 2.2 Paliers possibles (illustration, pas un engagement commercial)

Hypothèse : monnaie **EUR**, TVA selon cas — prix **TTC** affiché au consommateur UE.

| Offre | Public cible | Contenu typique | Fourchette indicative **mensuelle** | Remarques |
|-------|----------------|-----------------|--------------------------------------|-----------|
| **Free** | Découverte | Base limitée, local, peut‑être pub ou watermark discret | **0 €** | Objectif : acquisition et bouche‑à‑oreille. |
| **Pro individuel** | Artiste régulier | Catalogue étendu cloud, quota DL/mois, synchro | **~6 € – 15 € / mois** (ou **~60 € – 120 € / an**, −15 à −25 % vs mensuel) | Se situe sous beaucoup d’abonnements « créatif » larges ; au‑dessus des micro‑prix App Store si la valeur catalogue est là. |
| **Pro+ / Créateur** | Power user | Quotas plus hauts, packs inclus, priorité support | **~12 € – 25 € / mois** | À n’ouvrir que si la charge support + coûts CDN le justifient. |
| **École / Studio** | B2B | N sièges, facture, admin, éventuellement SLA léger | **~8 € – 20 € / siège / mois** (minimum de facturation) ou forfait annuel | Aligné conceptuellement sur des outils **par poste** (ex. références type viewer pro — **vérifier** concurrents directs au moment du pricing). |

**Règle empirique utile :** tester en **early access** un prix dans la moitié basse de la fourchette Pro, puis ajuster selon **rétention** et **coût marginal** au Go servi.

### 2.3 Autres revenus (vision produit)

- **Packs à l’unité** (achat ponctuel) : prix dépend des **droits** (photo studio vs droit d’auteur illustration). Pensée en **prix psychologique** (4,99 € / 9,99 € / 19,99 €) pour les petits packs.
- **Marketplace** (phase 2) : commission plateforme **15 % – 30 %** courante sur les places créatives — à trancher avec attractivité pour les vendeurs et charge légale/modération.

### 2.4 Ce qu’il ne faut pas oublier dans le prix

- **TVA / facturation** selon pays clients et statut de votre entité.
- **Remboursements / litiges** : provisionner du **support** et des pertes occasionnelles.
- **Devise** : si USD + clients UE, frais de change et pricing du PSP.

---

## 3. Estimation des coûts de mise en route d’un « service complet » (hors développement)

**Définition « service complet » minimal :** société ou statut adapté, **CGU / politique de confidentialité**, hébergement **API + base + stockage fichiers**, nom de domaine, emails transactionnels, **paiement** (Stripe ou équivalent), monitoring basique, comptabilité, et **distribution** (optionnel stores). **Exclu :** salaires développeurs, temps interne de code.

Les tableaux donnent des **fourchettes année 1** en **€** pour un projet **bootstrap** (peu d’utilisateurs au début) vs **préparation sérieuse** (trafic modéré, conformité renforcée).

### 3.1 Frais juridiques et administratifs

| Poste | Bootstrap (ordre de grandeur) | « Sérieux » |
|-------|-------------------------------|-------------|
| Création société / statut (France : SASU, etc.) | **200 € – 1 500 €** (guichet + honoraires si expert) | **1 000 € – 3 000 €** avec accompagnement |
| CGU + politique confidentialité + mentions (prestataire spécialisé) | **800 € – 2 500 €** | **2 000 € – 6 000 €** si international / marketplace |
| Comptabilité (expert-comptable ou outil + revue) | **1 200 € – 3 000 € / an** | **3 000 € – 8 000 € / an** |
| Dépôt marque (optionnel, INPI / EUIPO) | **0 €** (plus tard) | **1 000 € – 3 000 €+** selon zones |

*Les montants juridiques/compta varient fortement ; obtenir des devis.*

### 3.2 Infrastructure technique (cloud)

Hypothèse : backend conteneurisé ou PaaS, **PostgreSQL** managé, **stockage objet** (images), **CDN** pour téléchargements.

| Poste | Bootstrap (faible trafic) | Après traction légère |
|-------|---------------------------|------------------------|
| Nom de domaine + DNS | **10 € – 30 € / an** | Idem |
| Hébergement API (Railway, Fly.io, Render, etc.) | **0 € – 50 € / mois** (free tiers / petit plan) | **50 € – 300 € / mois** |
| Base PostgreSQL managée (Neon, Supabase, RDS, etc.) | **0 € – 25 € / mois** | **25 € – 150 € / mois** |
| Stockage objet + sortie (S3, R2, B2, etc.) | **Quelques € / mois** + **~0,01–0,09 €/Go** stocké selon fournisseur | **Monte avec Go** servis et nombre d’images |
| CDN / bande passante | Souvent inclus ou faible au début | **Variable** — peut devenir **poste majeur** si gros fichiers |
| Monitoring / logs (Sentry, etc.) | **0 € – 30 € / mois** | **30 € – 200 € / mois** |
| Emails transactionnels (SendGrid, Postmark, etc.) | **0 € – 20 € / mois** | Selon volume d’emails |

**Synthèse indicative année 1 infra (hors pic viral) :**  
- **~500 € – 3 000 € / an** en mode très sobre.  
- **~3 000 € – 15 000 € / an** si trafic et stockage montent vite (toujours sans ligne « dev »).

### 3.3 Paiements et distribution

| Poste | Coût typique |
|-------|----------------|
| **Stripe** (ou équivalent) | Pas de frais d’adhésion standard ; **commission par transaction** (ex. ordre de grandeur **~1,5 % + 0,25 € à ~2,9 % + 0,25 €** sur carte EU selon grille du PSP — **vérifier** [stripe.com/pricing](https://stripe.com/pricing) au jour J). |
| **Apple Developer Program** | **~99 $ / an** (facturé en devise locale) si distribution Mac/iOS. |
| **Google Play** | **Frais d’inscription** ponctuels (vérifier montant actuel). |
| **Microsoft Partner Center** | **Frais d’inscription** pour publier sur Microsoft Store (vérifier grille actuelle). |
| **Comptes test / sandbox** | Généralement inclus |

Les **frais de paiement** ne sont pas des « coûts de démarrage » fixes mais **réduisent la marge** sur chaque abonnement — à modéliser dans un tableur (MRR × (1 − taux PSP) − fixes).

### 3.4 Marketing et communication (minimum)

| Poste | Bootstrap | Plus visible |
|-------|-----------|----------------|
| Site vitrine (Webflow, Framer, ou statique) | **0 € – 200 € / an** (hors temps) | **200 € – 2 000 € / an** |
| Réseaux / contenu organique | Temps humain surtout | Idem + outils **~20 € – 100 € / mois** |
| Publicité (Meta, Google, YouTube) | **0 €** | **500 € – 10 000 €+** selon ambition — souvent **principal poste** hors dev si acquisition payante |

Sans budget pub, prévoir au minimum **temps** et éventuellement **500 € – 2 000 €** pour assets (logo, trailer, page produit) si externalisé.

### 3.5 Autres postes

| Poste | Commentaire |
|-------|-------------|
| **Assurance RC pro** | Selon activité et contrats B2B — **quelques centaines € / an** possible. |
| **Support** | Boîte mail pro (Google Workspace, Microsoft 365) **~5 € – 15 € / utilisateur / mois**. |
| **Contenu** | Si achat de banques d’images ou tournées photo : **variable**, souvent **le plus gros coût hors dev** pour un catalogue propriétaire de qualité. |

---

## 4. Synthèse : budget « hors dev » année 1 (fourchettes)

| Scénario | Description | Fourchette indicative **total année 1** (hors dev, hors achat massif de contenu) |
|----------|-------------|-------------------------------------------------------------------------------------|
| **A — Minimal viable** | Statut léger, infra free/low tier, peu de pub, docs juridiques correctes mais simples | **~3 000 € – 8 000 €** |
| **B — Structuré** | Société + expert-comptable + juriste solide + infra payante + monitoring + petite pub | **~10 000 € – 25 000 €** |
| **C — Avec acquisition contenu** | Comme B + **budget droits / production** d’images | **+5 000 € à plusieurs 100 k€** selon ambition catalogue |

**Rappel :** dès que le **stockage** et la **bande passante** explosent (gros fichiers, beaucoup de téléchargements), les coûts variables peuvent dépasser les coûts fixes — d’où l’intérêt des **quotas** et du **pricing** alignés sur le coût marginal.

---

## 5. Prochaines étapes utiles

1. **Valider** 2–3 **personas** (étudiant, freelance, école) et un **prix test** pour une beta payante.  
2. **Modéliser** en tableur : abonnements × utilisateurs × (1 − frais PSP) − infra − support.  
3. **Obtenir devis** juridique et comptable pour votre pays d’implantation.  
4. **Mesurer** coût au Go et par utilisateur actif dès les premiers mois sur un environnement de **staging** proche de la prod.

---

*Document de travail — à réviser lorsque le périmètre légal, le pays de vente et les fournisseurs cloud seront figés.*
