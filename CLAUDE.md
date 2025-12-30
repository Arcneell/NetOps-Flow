# Inframate

Plateforme de gestion IT complète (ITSM/ITAM) auto-hébergée, entièrement générée par IA (Claude).

**"Your Infrastructure Companion"** - Gestion helpdesk, inventaire, DCIM, IPAM, contrats et logiciels.

## Workflow Obligatoire

**Après chaque modification de code, Claude doit systématiquement :**

1. **Commit** les changements avec un message descriptif
2. **Push** vers le repository distant
3. **Mettre à jour README.md** si les changements affectent :
   - Les fonctionnalités documentées
   - Les instructions d'installation/utilisation
   - Les variables d'environnement
   - Les dépendances
4. **Mettre à jour CLAUDE.md** pour référencer :
   - Nouveaux fichiers/modules ajoutés
   - Nouvelles fonctionnalités
   - Changements d'architecture
   - Nouveaux endpoints API
   - Modifications de la structure de base de données

## Stack Technique

- **Backend**: FastAPI 0.109+ (lifespan context manager) + Python 3.11+ + SQLAlchemy 2.0 + Celery 5.3
- **Frontend**: Vue.js 3 + Pinia + PrimeVue 3.46 + TailwindCSS 3.4
- **Base de données**: PostgreSQL 15 + Redis 7
- **Containerisation**: Docker + Docker Compose (dev) / Docker Compose + Secrets (prod)

## Architecture

```
frontend/          # Vue.js 3 SPA
├── src/
│   ├── components/shared/   # Composants réutilisables (StatusTag, NotificationBell)
│   ├── stores/              # Pinia stores (auth, ui, dcim, contracts, software, networkPorts, attachments, tickets, notifications)
│   ├── views/               # Pages principales (Tickets.vue, Knowledge.vue pour helpdesk)
│   ├── i18n/                # Traductions EN/FR
│   ├── api.js               # Client Axios
│   ├── router.js            # Routes avec guards de permissions
│   └── style.css            # Design System Modern Slate (Anthracite, Zinc, Bleu électrique)

backend/           # FastAPI API
├── core/
│   ├── config.py           # Configuration Pydantic Settings (Docker secrets support, URL validation)
│   ├── database.py         # SQLAlchemy engine + sessions
│   ├── security.py         # JWT, bcrypt, Fernet encryption, TOTP (pyotp), refresh tokens (timezone-aware)
│   ├── rate_limiter.py     # Rate limiting Redis
│   ├── logging.py          # Logging structuré JSON/Text
│   ├── cache.py            # Cache Redis pour dashboard/topology (TTL 5min)
│   └── middleware.py       # Audit middleware (log auto POST/PUT/DELETE, enhanced metadata for critical ops)
├── routers/
│   ├── auth.py             # POST /token, GET /me, MFA, refresh tokens (/refresh, /logout, /logout-all)
│   ├── users.py            # CRUD utilisateurs (admin)
│   ├── ipam.py             # Subnets, IPs, scan nmap (paginé)
│   ├── topology.py         # Données visualisation réseau + topologie physique (caché)
│   ├── scripts.py          # Upload (validation MIME), exécution scripts (sandbox Docker obligatoire)
│   ├── inventory.py        # Équipements, fabricants, fournisseurs (auto-encryption passwords)
│   ├── dashboard.py        # Statistiques (caché Redis)
│   ├── dcim.py             # Gestion Racks et PDUs (optimisé avec joinedload)
│   ├── contracts.py        # Contrats de maintenance/assurance (paginé)
│   ├── software.py         # Catalogue logiciels et licences (paginé)
│   ├── network_ports.py    # Ports réseau et connexions physiques
│   ├── attachments.py      # Pièces jointes (documents)
│   ├── entities.py         # Entités multi-tenant
│   ├── tickets.py          # Système de tickets helpdesk (ITIL workflow, SLA, commentaires)
│   ├── notifications.py    # Notifications in-app (polling, mark read, broadcast)
│   └── knowledge.py        # Base de connaissances (articles, catégories, feedback)
├── models.py               # Modèles SQLAlchemy (+ UserToken, auto-encryption hooks pour TOTP/passwords)
├── schemas.py              # Schémas Pydantic (+ TokenWithRefresh, RefreshTokenRequest)
└── app.py                  # Application FastAPI (lifespan context manager, optimized health check)

worker/            # Celery worker
└── tasks.py       # Tâches async (exécution scripts, scan subnet, alertes expirations, collecte logiciels, cleanup tokens/audit logs)

frontend/src/utils/
└── validation.js  # Schémas de validation Zod (avatar, scripts, passwords, MFA codes)
```

## Fonctionnalités Principales

### IPAM (IP Address Management)
- Création de subnets avec validation CIDR
- Scan automatique via nmap pour découverte d'hôtes
- Liaison IP-équipement bidirectionnelle

### Automatisation Scripts
- Upload scripts Python, Bash, PowerShell
- Exécution locale dans sandbox Docker isolé
- Exécution distante via SSH (Linux) ou WinRM (Windows)
- Historique d'exécution avec stdout/stderr

### Inventaire (type GLPI)
- Gestion équipements avec cycle de vie complet
- Hiérarchie: Fabricant → Modèle → Équipement
- Localisation: Site → Bâtiment → Salle
- Statuts: En service, En stock, Retiré, Maintenance
- Intégration DCIM : Champs de placement rack (rack_id, position_u, height_u) dans le formulaire équipement
- Chargement automatique de la liste des baies pour sélection directe

### Topologie Réseau
- Visualisation graphique avec Vis.js
- Nodes colorés (vert=actif, gris=disponible)
- Topologie physique basée sur les connexions de ports

### DCIM (Data Center Infrastructure Management)
- Gestion des baies (racks) par emplacement
- Position U (1-42) et hauteur U des équipements
- Gestion des PDUs avec ports et alimentation
- Visualisation professionnelle des baies avec style hardware (bordures métalliques, numérotation U des deux côtés)
- Couleurs par statut d'équipement (bleu=en service, orange=maintenance, gris=retiré, vert=stock)
- Détails complets de l'équipement dans la vue rack (modèle, fabricant, S/N, asset tag, IP management)
- Liste des équipements non assignés avec placement interactif
- Validation des conflits de position lors du placement
- Tooltips détaillés au survol des équipements
- Navigation vers fiche équipement (Inventaire) au clic
- Menu contextuel (clic-droit) sur équipements : Voir détails, Changer position, Retirer de la baie
- Modification de position à chaud depuis la vue rack
- Retrait d'équipement du rack avec confirmation

### Gestion des Contrats
- Contrats de maintenance, assurance, location
- Liaison contrats-équipements multiples
- Alertes d'expiration automatiques (30 jours)
- Suivi des coûts annuels et renouvellements

### Inventaire Logiciel & Licences
- Catalogue logiciels avec éditeur et catégorie
- Gestion des licences (clé, quantité, expiration)
- Suivi des installations par équipement
- Calcul de conformité licences (installations vs quotas)
- Collecte automatique via SSH/WinRM

### Connectivité Physique
- Ports réseau par équipement (type, vitesse, MAC)
- Connexions bidirectionnelles port-à-port
- Mapping switch-serveur complet

### Gestion Documentaire
- Pièces jointes par équipement
- Catégorisation des documents
- Upload/Download sécurisé

### Multi-Tenant (Entités)
- Isolation des données par entité
- Filtrage automatique des résultats API
- Gestion des entités (admin)

### Authentification à Deux Facteurs (MFA/TOTP)
- Activation optionnelle par utilisateur via Settings
- Secrets TOTP générés avec pyotp et chiffrés en base (Fernet)
- QR code pour scan avec Google Authenticator, Authy, etc.
- Flux de connexion en 2 étapes : mot de passe puis code à 6 chiffres
- Désactivation sécurisée avec vérification du mot de passe
- Audit complet des événements MFA dans AuditLog

### Helpdesk - Système de Tickets
- Workflow ITIL : new → open → pending → resolved → closed
- Types de tickets : incident, request, problem, change
- Priorités : low, medium, high, critical
- Numérotation automatique : TKT-YYYYMMDD-XXXX
- Assignation à un utilisateur ou équipe
- SLA automatique basé sur la priorité (configurable via SLAPolicy)
- Temps de réponse et résolution calculés
- Commentaires avec distinction interne/public
- Historique complet des modifications
- Pièces jointes par ticket
- Filtrage par statut, priorité, assigné, dates
- Actions rapides : assigner, résoudre, fermer, rouvrir

### Base de Connaissances
- Articles avec éditeur Markdown
- Catégorisation et tags
- Recherche full-text (titre, contenu, résumé)
- URL basée sur slug unique
- Système de feedback (helpful/not helpful)
- Compteur de vues
- Versioning des articles
- Workflow publication : brouillon → publié
- Articles internes (admin/tech uniquement)
- Articles populaires (top vues)

### Notifications In-App
- Cloche de notification dans le header
- Badge compteur de non-lus
- Types : info, success, warning, error, ticket
- Polling automatique (30 secondes)
- Marquer comme lu (individuel ou tous)
- Lien vers ressource associée (ticket, article)
- Suppression des notifications lues
- Broadcast admin vers tous les utilisateurs

## Sécurité

- **Auth**: JWT (30min access token) + Refresh tokens (7 jours) + bcrypt pour mots de passe
- **Refresh Tokens**: Rotation automatique, révocation individuelle ou globale, stockage haché (SHA256), nettoyage automatique via Celery Beat
- **MFA/TOTP**: Authentification à deux facteurs optionnelle avec pyotp (secrets auto-chiffrés via hooks SQLAlchemy)
- **Encryption**: Fernet pour données sensibles (remote passwords, TOTP secrets)
- **Auto-Encryption**: Hooks SQLAlchemy pour chiffrer automatiquement Equipment.remote_password et User.totp_secret
- **Configuration Sécurisée**:
  - JWT_SECRET_KEY et ENCRYPTION_KEY obligatoires (validation Pydantic)
  - Support Docker secrets via *_FILE environment variables
  - Validation basique des URLs (supporte les mots de passe avec caractères spéciaux)
- **Timezone-Aware**: Utilisation de `datetime.now(timezone.utc)` (Python 3.12+ compatible)
- **Rate Limiting**: Redis-backed, 5 req/60s sur login
- **RBAC**: Rôles admin/user + permissions granulaires (ipam, scripts, inventory, topology, settings, tickets, knowledge)
- **Sandbox Docker**: Mémoire 256MB, CPU 0.5, network disabled, read-only filesystem
- **Sandbox Obligatoire**: Pas de fallback vers exécution directe quand DOCKER_SANDBOX_ENABLED=true
- **Validation MIME**: Vérification du type MIME des scripts uploadés (anti-masquage)
- **Audit Log**: Traçabilité complète via middleware (POST, PUT, DELETE) + événements MFA + métadonnées enrichies pour actions critiques (severity, category, affected_ids)
- **Validation Frontend**: Schémas Zod pour validation des fichiers (avatar, scripts) et formulaires (password, MFA code)
- **Cache Redis**: Dashboard et Topology cachés (TTL 5 minutes)

## Commandes

```bash
# Démarrage (développement)
docker-compose up --build

# Démarrage (production avec Docker secrets)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Logs
docker-compose logs -f backend
docker-compose logs -f worker

# Migrations
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"

# Base de données
docker-compose exec db psql -U inframate inframate

# Création des secrets Docker (production)
echo "your-jwt-secret" | docker secret create jwt_secret_key -
echo "your-encryption-key" | docker secret create encryption_key -
echo "your-admin-password" | docker secret create initial_admin_password -
echo "your-db-password" | docker secret create postgres_password -
```

## URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Variables d'Environnement Clés

| Variable | Défaut | Description |
|----------|--------|-------------|
| POSTGRES_PASSWORD | inframatepassword | Mot de passe PostgreSQL |
| JWT_SECRET_KEY | **(REQUIS)** | Clé secrète JWT (ou JWT_SECRET_KEY_FILE pour Docker secrets) |
| ENCRYPTION_KEY | **(REQUIS)** | Clé Fernet (ou ENCRYPTION_KEY_FILE pour Docker secrets) |
| INITIAL_ADMIN_PASSWORD | - | Mot de passe admin initial (ou INITIAL_ADMIN_PASSWORD_FILE) |
| ALLOWED_ORIGINS | http://localhost:3000 | CORS origins |
| LOG_LEVEL | INFO | Niveau de log |
| DOCKER_SANDBOX_MEMORY | 256m | Limite mémoire sandbox |
| SCRIPT_EXECUTION_TIMEOUT | 300 | Timeout scripts (sec) |

### Support Docker Secrets (Production)

En production, les secrets peuvent être lus depuis des fichiers via les variables `*_FILE`:
- `JWT_SECRET_KEY_FILE=/run/secrets/jwt_secret_key`
- `ENCRYPTION_KEY_FILE=/run/secrets/encryption_key`
- `INITIAL_ADMIN_PASSWORD_FILE=/run/secrets/initial_admin_password`

## Credentials par Défaut

- **Admin**: admin / (défini par INITIAL_ADMIN_PASSWORD, MFA désactivé par défaut)
- **Database**: inframate / inframatepassword / inframate

## Activation MFA (TOTP)

1. Se connecter avec admin/admin
2. Aller dans Settings → Security
3. Cliquer sur "Enable 2FA"
4. Scanner le QR code avec Google Authenticator, Authy, etc.
5. Entrer le code à 6 chiffres pour confirmer
6. À la prochaine connexion, le code TOTP sera demandé après le mot de passe

## Conventions de Code

### Python (Backend)
- PEP 8, type hints requis
- Fonctions courtes et focalisées
- Docstrings pour fonctions publiques

### Vue.js (Frontend)
- Composition API avec `<script setup>`
- Pinia pour state management
- Composants dans `components/shared/` pour réutilisation
- **i18n**: Utiliser `useI18n()` hook avec `legacy: false`
  - Clés hiérarchiques: `t('namespace.key')` (ex: `t('dashboard.totalSubnets')`)
  - Ne jamais utiliser `.value` sur `t()` - retourne directement une string
  - Namespaces: `common`, `nav`, `auth`, `dashboard`, `ipam`, `inventory`, `scripts`, `settings`, `users`, `validation`, `messages`, `filters`, `status`, `ip`, `remote`, `dcim`, `contracts`, `software`, `entities`, `tickets`, `knowledge`, `notifications`

### Design System (Modern Slate)
- **Palette de couleurs**:
  - Light: Zinc 50 (#fafafa) + Zinc 900 (#18181b) + Electric Blue (#0ea5e9)
  - Dark: Slate 950 (#0f172a) + Slate 50 (#f8fafc) + Electric Blue (#0ea5e9)
- **Composants**:
  - Cards: `rounded-xl` + `backdrop-blur` + ombre progressive au hover
  - Dialogs: `rounded-xl` + `backdrop-blur(12px)` + ombre profonde
  - Sidebar: Width 16rem + gradient header + sliding accent bar (3px electric blue)
  - StatusTag: Gradients avec icônes contextuelles (check-circle, wrench, shield, etc.)
- **Animations**:
  - Transitions: `cubic-bezier(0.4, 0, 0.2, 1)` à 0.15s
  - Hover: `translateY(-1px)` ou `translateX(2px)` selon contexte
  - Micro-animations sur sidebar links avec `scaleY()` pour accent bar

### Git
- Messages clairs commençant par verbe (Add, Fix, Update)
- Pas de secrets dans les commits
- **IMPORTANT**: Toujours commit avec l'utilisateur `Arcneell` (arcneel.pro@gmail.com)
  - Vérifier la configuration: `git config user.name` et `git config user.email`
  - Si incorrecte, corriger avec: `git config --global user.name "Arcneell" && git config --global user.email "arcneel.pro@gmail.com"`

## Structure Base de Données

**Tables principales:**
- `users` - Utilisateurs avec rôles, permissions et MFA (colonnes: mfa_enabled, totp_secret auto-chiffré via hook)
- `user_tokens` - Refresh tokens (token_hash SHA256, expires_at, revoked, device_info, ip_address)
- `entities` - Entités multi-tenant
- `subnets` / `ip_addresses` - IPAM
- `scripts` / `script_executions` - Automatisation
- `manufacturers` / `equipment_types` / `equipment_models` - Catalogue
- `locations` / `suppliers` / `equipment` - Inventaire (remote_password auto-chiffré via hook)
- `racks` / `pdus` - DCIM
- `contracts` / `contract_equipment` - Contrats
- `software` / `software_licenses` / `software_installations` - Logiciels
- `network_ports` - Ports réseau et connexions
- `attachments` - Pièces jointes
- `audit_logs` - Logs de modifications (remplis automatiquement par middleware)
- `tickets` - Tickets helpdesk (ticket_number unique, workflow ITIL, SLA)
- `ticket_comments` - Commentaires tickets (interne/public, is_resolution)
- `ticket_history` - Historique modifications tickets
- `ticket_attachments` - Pièces jointes par ticket
- `notifications` - Notifications in-app (type, lu/non-lu, lien ressource)
- `knowledge_articles` - Articles base de connaissances (slug, versioning, feedback)
- `sla_policies` - Politiques SLA configurables par priorité

**Hooks SQLAlchemy (before_insert/before_update):**
- `Equipment.remote_password` → chiffré automatiquement avec Fernet
- `User.totp_secret` → chiffré automatiquement avec Fernet

## API Endpoints Principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| /api/v1/auth/token | POST | Login, obtenir access + refresh tokens ou challenge MFA |
| /api/v1/auth/refresh | POST | Renouveler access token avec refresh token (rotation) |
| /api/v1/auth/logout | POST | Révoquer refresh token (déconnexion) |
| /api/v1/auth/logout-all | POST | Révoquer tous les refresh tokens (toutes sessions) |
| /api/v1/auth/verify-mfa | POST | Vérifier code TOTP et obtenir tokens |
| /api/v1/auth/mfa/setup | POST | Générer secret TOTP et URI QR code |
| /api/v1/auth/mfa/enable-with-secret | POST | Activer MFA après vérification code |
| /api/v1/auth/mfa/disable | POST | Désactiver MFA (requiert mot de passe) |
| /api/v1/auth/me | GET | Info utilisateur courant |
| /api/v1/subnets/ | GET/POST | Liste/Créer subnets |
| /api/v1/subnets/{id}/scan | POST | Scanner subnet (nmap) |
| /api/v1/scripts/ | GET/POST | Liste/Upload scripts |
| /api/v1/scripts/{id}/run | POST | Exécuter script |
| /api/v1/executions/ | GET | Historique exécutions |
| /api/v1/inventory/equipment/ | GET/POST | Équipements |
| /api/v1/dashboard/stats | GET | Statistiques |
| /api/v1/dcim/racks/ | GET/POST | Baies |
| /api/v1/dcim/racks/{id}/layout | GET | Disposition baie (détails complets équipements + non assignés) |
| /api/v1/dcim/racks/{id}/place-equipment | POST | Placer équipement dans baie (avec validation conflits) |
| /api/v1/dcim/equipment/{id}/rack-position | PUT | Modifier position équipement dans baie |
| /api/v1/dcim/equipment/{id}/rack-position | DELETE | Retirer équipement de la baie |
| /api/v1/dcim/pdus/ | GET/POST | PDUs |
| /api/v1/contracts/ | GET/POST | Contrats |
| /api/v1/contracts/{id}/equipment | GET/POST/DELETE | Équipements contrat |
| /api/v1/software/ | GET/POST | Catalogue logiciels |
| /api/v1/software/{id}/licenses | GET/POST | Licences |
| /api/v1/software/{id}/installations | GET/POST | Installations |
| /api/v1/network-ports/ | GET/POST | Ports réseau |
| /api/v1/network-ports/{id}/connect | POST | Connecter ports |
| /api/v1/attachments/ | GET/POST | Pièces jointes |
| /api/v1/entities/ | GET/POST | Entités |
| /api/v1/topology/physical | GET | Topologie physique |
| /api/v1/tickets/ | GET/POST | Liste/Créer tickets |
| /api/v1/tickets/{id} | GET/PUT/DELETE | Détail/Modifier/Supprimer ticket |
| /api/v1/tickets/{id}/comments | GET/POST | Commentaires ticket |
| /api/v1/tickets/{id}/history | GET | Historique ticket |
| /api/v1/tickets/{id}/assign | POST | Assigner ticket |
| /api/v1/tickets/{id}/resolve | POST | Résoudre ticket |
| /api/v1/tickets/{id}/close | POST | Fermer ticket |
| /api/v1/tickets/{id}/reopen | POST | Rouvrir ticket |
| /api/v1/tickets/stats | GET | Statistiques tickets |
| /api/v1/notifications/ | GET | Liste notifications |
| /api/v1/notifications/count | GET | Compteur non-lus |
| /api/v1/notifications/{id}/read | POST | Marquer comme lu |
| /api/v1/notifications/read-all | POST | Marquer tous comme lus |
| /api/v1/notifications/delete-read | DELETE | Supprimer les lus |
| /api/v1/notifications/broadcast | POST | Broadcast admin |
| /api/v1/knowledge/articles | GET/POST | Liste/Créer articles KB |
| /api/v1/knowledge/articles/{slug} | GET | Article par slug |
| /api/v1/knowledge/articles/{id} | PUT/DELETE | Modifier/Supprimer article |
| /api/v1/knowledge/articles/{id}/feedback | POST | Feedback article |
| /api/v1/knowledge/articles/{id}/publish | POST | Publier article |
| /api/v1/knowledge/articles/{id}/unpublish | POST | Dépublier article |
| /api/v1/knowledge/articles/categories | GET | Liste catégories |
| /api/v1/knowledge/articles/popular | GET | Articles populaires |

## Troubleshooting

**Connexion DB échoue**: Vérifier `docker-compose logs db`, credentials .env

**Worker ne traite pas les tâches**: `docker-compose logs worker`, vérifier Redis

**401 Unauthorized**: Token expiré, re-login

**429 Too Many Requests**: Rate limited, attendre 60 secondes

**Sandbox Docker indisponible**: Rebuild image `docker build -t inframate-sandbox:latest -f docker/sandbox.Dockerfile .`

**Build échoue sur macOS (Apple Silicon)**: PowerShell n'est installé que sur AMD64. Sur ARM64, l'exécution distante via WinRM ne sera pas disponible en développement (SSH reste fonctionnel)
