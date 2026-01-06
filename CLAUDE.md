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
│   ├── stores/              # Pinia stores (auth, ui, dcim, contracts, software, networkPorts, attachments, tickets, notifications, inventory)
│   ├── views/               # Pages principales (Tickets.vue, Knowledge.vue, Administration.vue)
│   ├── i18n/                # Traductions EN/FR
│   ├── api.js               # Client Axios
│   ├── router.js            # Routes avec guards de permissions (lazy loading, code splitting)
│   └── style.css            # Design System Modern Slate (Anthracite, Zinc, Bleu électrique)

backend/           # FastAPI API
├── core/
│   ├── config.py           # Configuration Pydantic Settings (Docker secrets support, URL validation)
│   ├── database.py         # SQLAlchemy engine + sessions
│   ├── security.py         # JWT, bcrypt, Fernet encryption, TOTP (pyotp), refresh tokens, password strength validation (regex)
│   ├── rate_limiter.py     # Rate limiting Redis (login, MFA, settings)
│   ├── logging.py          # Logging structuré JSON/Text
│   ├── cache.py            # Cache Redis pour dashboard/topology/tickets/inventory (TTL 2-5min, invalidation intelligente)
│   ├── middleware.py       # Audit middleware (log auto POST/PUT/DELETE, optimisé avec JWT claims)
│   └── sla.py              # Calcul SLA avec heures ouvrées (BusinessHoursCalculator)
├── routers/
│   ├── auth.py             # POST /token, GET /me, MFA, refresh tokens (/refresh, /logout, /logout-all)
│   ├── users.py            # CRUD utilisateurs (admin)
│   ├── ipam.py             # Subnets, IPs, scan nmap (paginé)
│   ├── topology.py         # Données visualisation réseau + topologie physique (caché)
│   ├── scripts.py          # Upload (validation MIME), exécution scripts (sandbox Docker obligatoire)
│   ├── inventory.py        # Équipements, fabricants, fournisseurs (joinedload optimisé, cache Redis, auto-encryption)
│   ├── dashboard.py        # Statistiques (caché Redis)
│   ├── dcim.py             # Gestion Racks et PDUs (optimisé avec joinedload)
│   ├── contracts.py        # Contrats de maintenance/assurance (paginé)
│   ├── software.py         # Catalogue logiciels et licences (paginé)
│   ├── network_ports.py    # Ports réseau et connexions physiques
│   ├── attachments.py      # Pièces jointes (documents)
│   ├── entities.py         # Entités multi-tenant
│   ├── tickets.py          # Système de tickets helpdesk (ITIL workflow, SLA business hours, ticket_number atomique via advisory lock)
│   ├── notifications.py    # Notifications in-app (polling, mark read, broadcast)
│   ├── knowledge.py        # Base de connaissances (articles, catégories, feedback)
│   ├── export.py           # Export CSV (équipements, tickets, contrats, logiciels, IPs, audit)
│   ├── search.py           # Recherche globale multi-ressources
│   ├── webhooks.py         # Webhooks pour intégrations externes (Slack, Teams, etc.)
│   └── settings.py         # Configuration système (SMTP, général, sécurité, notifications, maintenance, rate limited)
├── models.py               # Modèles SQLAlchemy (+ EncryptedString TypeDecorator, ticket_number hook, UserToken)
├── schemas.py              # Schémas Pydantic (+ TokenWithRefresh, RefreshTokenRequest)
└── app.py                  # Application FastAPI (lifespan context manager, auto create_default_admin)

worker/            # Celery worker
└── tasks.py       # Tâches async (exécution scripts, scan subnet, alertes expirations, collecte logiciels, cleanup tokens/audit logs, SLA breach check, backup PostgreSQL)

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
- **QR Codes** : Génération de QR codes pour équipements (PNG ou base64, taille configurable)

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
- Numérotation automatique : TKT-YYYYMMDD-XXXX (via SQLAlchemy hook atomique)
- Assignation à un utilisateur ou équipe
- SLA automatique basé sur la priorité (configurable via SLAPolicy)
- **SLA avec heures ouvrées** : Calcul respectant les jours/heures ouvrés
- Temps de réponse et résolution calculés
- **Détection automatique breach SLA** (toutes les 15 min via Celery Beat)
- Commentaires avec distinction interne/public
- Historique complet des modifications
- Pièces jointes par ticket
- Filtrage par statut, priorité, assigné, dates
- Actions rapides : assigner, résoudre, fermer, rouvrir
- **Statistiques cachées** (Redis, TTL 2 min)
- **Modèles de tickets** : Templates prédéfinis pour création rapide (titre, description, type, priorité, catégorie)

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

### Export de Données
- Export CSV pour équipements, tickets, contrats, logiciels, IPs, audit logs
- Filtres sur dates, statuts, types
- Noms de fichiers horodatés

### Recherche Globale
- Recherche unifiée sur équipements, tickets, articles KB, subnets, contrats, logiciels
- Filtrage par type de ressource
- Résultats groupés avec score de pertinence
- Contrôle d'accès basé sur les rôles

### Webhooks (Intégrations)
- Webhooks pour événements : ticket.created, ticket.resolved, equipment.created, sla.breached, etc.
- Signature HMAC avec secret partagé
- Retries automatiques avec backoff exponentiel
- Logs de livraison pour debugging
- Test de webhook depuis l'interface

### Administration Système (Superadmin uniquement)
- Configuration SMTP : serveur email avec support TLS et test de connexion
- Paramètres généraux : nom du site, URL, langue par défaut, timeout session
- Paramètres de sécurité : politique mot de passe, exigence MFA, rate limiting
- Paramètres de notifications : emails, alertes d'expiration contrats/licences
- Mode maintenance : activation, message personnalisé, rétention audit logs
- **Backups PostgreSQL** : Sauvegarde automatique via Celery (pg_dump, compression gzip optionnelle)
- **Nettoyage backups** : Suppression automatique des anciens backups (rétention configurable)

## Optimisations de Performance

### Backend
- **N+1 Queries Prevention** : Utilisation systématique de `joinedload()` et `selectinload()` dans tous les routers (inventory, dcim, topology, tickets)
- **Cache Redis** : TTL 2-5 minutes pour dashboard, topology, tickets stats, et inventory avec invalidation intelligente lors des mutations
- **Audit Middleware Optimisé** : Extraction des infos utilisateur depuis JWT claims (user_id, role) sans requête DB supplémentaire
- **Ticket Number Generation** : Utilisation de `pg_advisory_xact_lock` pour garantir l'atomicité sous forte charge
- **Index de Performance** :
  - Index basiques : `ix_ip_addresses_hostname`, `ix_ip_addresses_status`, `ix_ip_addresses_subnet_id`
  - Index GIN sur colonnes JSON : `permissions`, `specs`, `tags`, `events`, `changes`, `extra_data`
  - Index partiels : équipements actifs, notifications non-lues, tickets ouverts
  - Index composites pour requêtes fréquentes

### Frontend
- **Lazy Loading Routes** : Code splitting avec `import()` dynamique pour toutes les routes sauf Login/Dashboard/Unauthorized
- **Pinia Stores avec Cache Local** : TTL 2 minutes côté client, debounce des appels, mises à jour optimistes
- **Invalidation Intelligente** : Cache invalidé automatiquement lors des mutations (create, update, delete)

### Fichier de Migration
- `backend/migrations/001_performance_indexes.sql` : Script SQL à exécuter pour ajouter tous les index de performance

## Sécurité

- **Auth**: JWT (30min access token) + Refresh tokens (7 jours) + bcrypt pour mots de passe
- **Refresh Tokens**: Rotation automatique, révocation individuelle ou globale, stockage haché (SHA256), nettoyage automatique via Celery Beat
- **MFA/TOTP**: Authentification à deux facteurs optionnelle avec pyotp (secrets auto-chiffrés via TypeDecorator)
- **Encryption**: Fernet pour données sensibles (remote passwords, TOTP secrets)
- **EncryptedString TypeDecorator**: Chiffrement/déchiffrement automatique transparent via SQLAlchemy TypeDecorator (remplace les hooks manuels)
- **Password Policy**: Validation renforcée avec regex (min 8 caractères + majuscule + minuscule + chiffre + caractère spécial)
- **Configuration Sécurisée**:
  - JWT_SECRET_KEY et ENCRYPTION_KEY obligatoires (validation Pydantic)
  - Support Docker secrets via *_FILE environment variables
  - Validation basique des URLs (supporte les mots de passe avec caractères spéciaux)
- **Timezone-Aware**: Utilisation de `datetime.now(timezone.utc)` (Python 3.12+ compatible)
- **Rate Limiting**: Redis-backed
  - Login: 5 req/60s
  - MFA verification: protection brute force
  - SystemSettings: 10 modifications/min par utilisateur
- **RBAC Hiérarchique**:
  - `user`: Helpdesk uniquement (tickets, base de connaissances)
  - `tech`: Permissions granulaires (ipam, inventory, dcim, contracts, software, topology, knowledge, tickets_admin, etc.)
  - `admin`: Toutes permissions tech + gestion utilisateurs
  - `superadmin`: Accès complet (scripts, paramètres système)
- **Permissions Granulaires**: ipam, inventory, dcim, contracts, software, topology, knowledge, network_ports, attachments, tickets_admin, reports
- **Sandbox Docker**: Mémoire 256MB, CPU 0.5, network disabled, read-only filesystem
- **Sandbox Obligatoire**: Pas de fallback vers exécution directe quand DOCKER_SANDBOX_ENABLED=true
- **Validation MIME**: Vérification du type MIME des scripts uploadés (anti-masquage)
- **Audit Log**: Traçabilité complète via middleware (POST, PUT, DELETE) + événements MFA + métadonnées enrichies pour actions critiques (severity, category, affected_ids)
- **Validation Frontend**: Schémas Zod pour validation des fichiers (avatar, scripts) et formulaires (password, MFA code)
- **Cache Redis**: Dashboard, Topology et Ticket Stats cachés (TTL 2-5 minutes)
- **Init Admin Automatique**: Création automatique du superadmin au démarrage via lifespan context manager

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
| BACKUP_DIR | /backups | Répertoire de stockage des backups |
| BACKUP_RETENTION_DAYS | 30 | Durée de rétention des backups (jours) |

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
  - Namespaces: `common`, `nav`, `auth`, `dashboard`, `ipam`, `inventory`, `scripts`, `settings`, `users`, `validation`, `messages`, `filters`, `status`, `ip`, `remote`, `dcim`, `contracts`, `software`, `entities`, `tickets`, `knowledge`, `notifications`, `admin`, `roles`, `permissions`

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
- `users` - Utilisateurs avec rôles hiérarchiques (user, tech, admin, superadmin), permissions JSON et MFA (totp_secret auto-chiffré)
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
- `system_settings` - Paramètres système (key, value JSON, category, is_sensitive)
- `knowledge_articles` - Articles base de connaissances (slug, versioning, feedback)
- `sla_policies` - Politiques SLA configurables par priorité (+ heures ouvrées)
- `webhooks` - Configuration webhooks externes (events, url, secret HMAC)
- `webhook_deliveries` - Logs de livraison webhooks (status, response, retries)
- `ticket_templates` - Modèles de tickets prédéfinis (titre, description, type, priorité, catégorie, icône)

**SQLAlchemy TypeDecorators & Hooks:**
- `EncryptedString` TypeDecorator → chiffrement/déchiffrement automatique transparent (utilisé pour totp_secret, remote_password)
- `Ticket.ticket_number` → généré automatiquement via hook `before_insert` (format: TKT-YYYYMMDD-XXXX, numérotation séquentielle atomique)

**Index de performance:**
- `ix_equipment_status` - Filtrage par statut équipement
- `ix_equipment_entity_id` - Filtrage multi-tenant
- `ix_equipment_asset_tag` - Recherche par asset tag
- `ix_tickets_status` - Filtrage par statut ticket
- `ix_tickets_priority` - Filtrage par priorité
- `ix_tickets_created_by` - Tickets par créateur
- `ix_tickets_assigned_to` - Tickets par assigné
- `ix_tickets_entity_id` - Filtrage multi-tenant
- `ix_audit_logs_timestamp` - Recherche temporelle audit
- `ix_audit_logs_user_id` - Audit par utilisateur
- `ix_audit_logs_action` - Audit par action
- `ix_contracts_end_date` - Alertes expiration
- `ix_contracts_status` - Filtrage par statut
- `ix_software_licenses_expiry` - Alertes expiration licences
- `ix_ip_addresses_status` - Filtrage IPAM
- `ix_ip_addresses_subnet_id` - IPs par subnet
- `ix_notifications_user_is_read` - Notifications non-lues
- `ix_knowledge_articles_is_published` - Articles publiés

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
| /api/v1/inventory/equipment/{id}/qrcode | GET | QR code équipement (PNG ou base64) |
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
| /api/v1/tickets/templates/ | GET/POST | Liste/Créer modèles de tickets |
| /api/v1/tickets/templates/{id} | GET/PUT/DELETE | Détail/Modifier/Supprimer modèle |
| /api/v1/tickets/from-template | POST | Créer ticket depuis modèle |
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
| /api/v1/export/equipment | GET | Export CSV équipements |
| /api/v1/export/tickets | GET | Export CSV tickets |
| /api/v1/export/contracts | GET | Export CSV contrats |
| /api/v1/export/software | GET | Export CSV logiciels |
| /api/v1/export/ip-addresses | GET | Export CSV IPs |
| /api/v1/export/audit-logs | GET | Export CSV audit logs |
| /api/v1/search/ | GET | Recherche globale (q=query, types=...) |
| /api/v1/webhooks/ | GET/POST | Liste/Créer webhooks |
| /api/v1/webhooks/{id} | GET/PUT/DELETE | Détail/Modifier/Supprimer webhook |
| /api/v1/webhooks/{id}/test | POST | Tester webhook |
| /api/v1/webhooks/{id}/deliveries | GET | Logs de livraison |
| /api/v1/webhooks/events | GET | Liste événements disponibles |
| /api/v1/settings/ | GET | Liste paramètres système (superadmin) |
| /api/v1/settings/by-category | GET | Paramètres groupés par catégorie |
| /api/v1/settings/{key} | GET/PUT | Lire/Modifier paramètre |
| /api/v1/settings/test-smtp | POST | Tester connexion SMTP |

## Troubleshooting

**Connexion DB échoue**: Vérifier `docker-compose logs db`, credentials .env

**Worker ne traite pas les tâches**: `docker-compose logs worker`, vérifier Redis

**401 Unauthorized**: Token expiré, re-login

**429 Too Many Requests**: Rate limited, attendre 60 secondes

**Sandbox Docker indisponible**: Rebuild image `docker build -t inframate-sandbox:latest -f docker/sandbox.Dockerfile .`

**Build échoue sur macOS (Apple Silicon)**: PowerShell n'est installé que sur AMD64. Sur ARM64, l'exécution distante via WinRM ne sera pas disponible en développement (SSH reste fonctionnel)
