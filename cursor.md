# Inframate

**Fichier de contexte projet pour Cursor.** À @ mentionner (`@cursor.md`) pour que l'assistant ait le contexte à chaque session.

Plateforme de gestion IT complète (ITSM/ITAM) auto-hébergée. **"Your Infrastructure Companion"** — Gestion helpdesk, inventaire, DCIM, IPAM, contrats et logiciels.

## Workflow après modification

**Après des modifications de code, l'assistant :**

1. **Exécute le script de validation** : `python scripts/validate.py`
   - Vérifier les erreurs de syntaxe Python, les traductions i18n manquantes, la structure des fichiers Vue
   - Si des erreurs sont détectées, les corriger avant de continuer
2. **Met à jour README.md** si les changements affectent : fonctionnalités documentées, instructions d'installation/utilisation, variables d'environnement, dépendances
3. **Met à jour cursor.md** pour : nouveaux fichiers/modules, nouvelles fonctionnalités, changements d'architecture, nouveaux endpoints API, modifications de la structure de base de données

**Commit et push** : faits **manuellement** par l'utilisateur, pas par l'assistant.

## Script de Validation

Le script `scripts/validate.py` vérifie la qualité du code (syntaxe Python, JSON, i18n, structure Vue).

```bash
python scripts/validate.py          # Complet
python scripts/validate.py --quick  # Syntaxe uniquement
python scripts/validate.py --fix    # Suggestions traductions
python scripts/validate.py --ci     # Mode CI (exit non-zéro si erreur)
```

**Règles i18n** : format `namespace.key`, clés dans EN et FR, namespaces définis dans le script.

**Intégration** : l'assistant exécute ce script après des modifications et corrige les erreurs (ajout de clés i18n si manquantes). Commit et push restent manuels.

## Stack Technique

- **Backend** : FastAPI 0.109+ (lifespan) + Python 3.11+ + SQLAlchemy 2.0 + Celery 5.3
- **Frontend** : Vue.js 3 + Pinia + PrimeVue 3.46 + TailwindCSS 3.4
- **Base de données** : PostgreSQL 15 + Redis 7
- **Containerisation** : Docker + Docker Compose (dev) / Docker Compose + Secrets (prod)

## Architecture

```
frontend/          # Vue.js 3 SPA
├── src/
│   ├── components/shared/   # StatusTag, NotificationBell, CommandBar, Breadcrumbs, EmptyState, ExpiryBadge, SlideOver, *DetailSlideOver
│   ├── stores/              # Pinia: auth, ui, dcim, contracts, software, networkPorts, attachments, tickets, notifications, inventory, notification
│   ├── views/               # Tickets, Knowledge, Dashboard, Inventory, Ipam, Dcim, Contracts, Software, Settings, Administration…
│   ├── i18n/                # Traductions EN/FR
│   ├── api.js               # Client Axios (interceptors, refresh, toasts)
│   ├── router.js            # Routes, lazy loading, guards de permissions
│   ├── style.css            # Design System Modern Slate
│   └── utils/validation.js  # Zod (avatar, scripts, passwords, MFA)
backend/
├── core/          # config, database, security, rate_limiter, logging, cache, middleware, sla
├── routers/       # auth, users, ipam, topology, scripts, inventory, dashboard, dcim, contracts, software, network_ports, attachments, entities, tickets, notifications, knowledge, export, search, webhooks, settings
├── models.py      # SQLAlchemy, EncryptedString, ticket_number hook, UserToken
├── schemas.py     # Pydantic
└── app.py         # FastAPI, lifespan, create_default_admin
worker/tasks.py    # Celery: scripts, scan subnet, alertes expirations, collecte logiciels, cleanup, SLA breach, backup
```

## Pièges et règles techniques

### Frontend — Pinia / api.js
- Ne pas accéder à un store Pinia au top-level ou dans un interceptor sans garde. Dans `api.js`, le `notificationStore` est chargé de façon **lazy** (import dynamique + try/catch) pour éviter `getActivePinia() was called but there was no active Pinia` au chargement ou en cas d'erreur API avant le mount de Vue.

### Backend — EncryptedString
- Les colonnes `totp_secret` (User) et `remote_password` (Equipment) utilisent `EncryptedString`, qui **déchiffre automatiquement** à la lecture (`process_result_value`). **Ne jamais** appeler `decrypt_value()` sur ces champs (double déchiffrement / erreur). Ex. dans `verify_mfa` : utiliser `user.totp_secret` directement dans `verify_totp_code()`.

## Fonctionnalités principales

- **IPAM** : subnets, CIDR, scan nmap, liaison IP-équipement
- **Scripts** : upload Python/Bash/PowerShell, sandbox Docker, SSH/WinRM, historique
- **Inventaire** : Fabricant→Modèle→Équipement, localisation, statuts, DCIM (rack_id, position_u, height_u), QR codes
- **Topologie** : Vis.js, topologie physique (ports)
- **DCIM** : baies, U, PDUs, placement interactif, conflits, menu contextuel
- **Contrats** : maintenance/assurance/location, liaison équipements, alertes expiration
- **Logiciels** : catalogue, licences, installations, conformité, collecte SSH/WinRM
- **Ports réseau** : type, vitesse, MAC, connexions port-à-port
- **Pièces jointes** : par équipement, catégorisation
- **Multi-tenant** : entités, filtrage
- **MFA/TOTP** : optionnel, pyotp, Fernet, QR, audit
- **Tickets** : ITIL (new→open→pending→resolved→closed), types, priorités, TKT-YYYYMMDD-XXXX, SLA (heures ouvrées), breach auto (Celery), commentaires, historique, modèles
- **Knowledge** : Markdown, catégories dynamiques, tags, slug, feedback, versioning, publication
- **Notifications** : cloche, polling, deep linking, broadcast, alertes auto
- **UI** : Command Bar (Ctrl+K), breadcrumbs, slide-overs, ExpiryBadge, Empty States, micro-interactions
- **Export CSV** : équipements, tickets, contrats, logiciels, IPs, audit
- **Recherche globale** : multi-ressources, filtres
- **Webhooks** : événements, HMAC, retries, logs
- **Admin (superadmin)** : SMTP, général, sécurité, notifications, maintenance, backups, nettoyage backups

## Optimisations

- **Backend** : `joinedload`/`selectinload`, cache Redis (TTL 2–5 min), audit via JWT claims, `pg_advisory_xact_lock` pour ticket_number, index GIN/basiques/partiels
- **Frontend** : lazy loading des routes, cache Pinia (TTL 2 min), invalidation aux mutations
- **Index** : dans les modèles SQLAlchemy (`__table_args__`), créés au démarrage

## Sécurité

- JWT (30 min) + refresh (7 j, rotation, SHA256, Celery cleanup), bcrypt, MFA (pyotp, EncryptedString)
- Fernet (TOTP, remote_password), **EncryptedString = ne pas appeler decrypt_value en lecture**
- Password policy (regex), JWT_SECRET_KEY + ENCRYPTION_KEY requis, *_FILE pour Docker secrets
- Rate limiting Redis : login 5/60s, MFA, SystemSettings 10/min
- RBAC : user → tech → admin → superadmin ; permissions granulaires
- Sandbox Docker (256MB, no network, read-only), validation MIME, audit (middleware + MFA), Zod frontend, init admin au lifespan

## Commandes

```bash
docker-compose up --build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d  # prod + secrets
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec db psql -U inframate inframate
# Secrets: echo "x" | docker secret create jwt_secret_key -
```

## URLs

- Frontend : http://localhost:3000
- API : http://localhost:8000
- Docs : http://localhost:8000/docs

## Variables d'environnement

| Variable | Rôle |
|----------|------|
| JWT_SECRET_KEY / JWT_SECRET_KEY_FILE | Requis |
| ENCRYPTION_KEY / ENCRYPTION_KEY_FILE | Requis |
| INITIAL_ADMIN_PASSWORD / *_FILE | Admin initial |
| ALLOWED_ORIGINS | CORS |
| POSTGRES_PASSWORD | DB |
| LOG_LEVEL, DOCKER_SANDBOX_*, SCRIPT_EXECUTION_TIMEOUT | Divers |
| BACKUP_DIR, BACKUP_RETENTION_DAYS | Backups |

## Credentials

- **Admin** : admin / (INITIAL_ADMIN_PASSWORD), MFA désactivé par défaut
- **DB** : inframate / inframatepassword / inframate

## MFA (TOTP)

Settings → Security → Enable 2FA → scanner QR (Google Authenticator, Authy) → confirmer avec code 6 chiffres.

## Conventions de code

### Python
- PEP 8, type hints, docstrings

### Vue
- Composition API `<script setup>`, Pinia
- **i18n** : `t('namespace.key')`, pas de `.value` sur `t()`. Namespaces : common, nav, auth, dashboard, ipam, inventory, scripts, settings, users, validation, messages, filters, status, ip, remote, dcim, contracts, software, entities, tickets, knowledge, notifications, admin, roles, permissions

### Design System (Modern Slate)
- Light : Zinc 50/900 + Electric Blue #0ea5e9
- Dark : Slate 950/50 + Electric Blue
- Cards/dialogs : rounded-xl, backdrop-blur
- Sidebar : 16rem, accent bar 3px
- Transitions : cubic-bezier(0.4,0,0.2,1), hover translateY(-1px) ou translateX(2px)

### Git
- Messages : Add, Fix, Update. Pas de secrets. User : Arcneell (arcneel.pro@gmail.com).

## Structure Base de Données

**Tables** : users (rôles, permissions JSON, totp_secret EncryptedString), user_tokens, entities, subnets, ip_addresses, scripts, script_executions, manufacturers, equipment_types, equipment_models, locations, suppliers, equipment (remote_password EncryptedString), racks, pdus, contracts, contract_equipment, software, software_licenses, software_installations, network_ports, attachments, audit_logs, tickets, ticket_comments, ticket_history, ticket_attachments, notifications, system_settings, knowledge_categories, knowledge_articles, sla_policies, webhooks, webhook_deliveries, ticket_templates.

**EncryptedString** : totp_secret, remote_password — déchiffrement auto, ne pas appeler decrypt_value.

**Ticket.ticket_number** : hook `before_insert`, TKT-YYYYMMDD-XXXX, `pg_advisory_xact_lock` (PostgreSQL).

**Index** : ix_equipment_*, ix_tickets_*, ix_audit_logs_*, ix_contracts_*, ix_software_licenses_*, ix_ip_addresses_*, ix_notifications_*, ix_knowledge_articles_*, GIN sur JSON/JSONB.

## API Endpoints principaux

| Endpoint | Description |
|----------|-------------|
| /api/v1/auth/token | Login, tokens ou challenge MFA |
| /api/v1/auth/refresh, /logout, /logout-all | Refresh (rotation), logout |
| /api/v1/auth/verify-mfa | Vérifier TOTP, obtenir tokens |
| /api/v1/auth/mfa/setup, enable-with-secret, disable | MFA |
| /api/v1/auth/me | Utilisateur courant |
| /api/v1/subnets/, /{id}/scan | Subnets, nmap |
| /api/v1/scripts/, /{id}/run, /executions/ | Scripts, exécution, historique |
| /api/v1/inventory/equipment/, /{id}/qrcode | Équipements, QR |
| /api/v1/dashboard/stats | Stats |
| /api/v1/dcim/racks/, /{id}/layout, /place-equipment | Baies, layout, placement |
| /api/v1/dcim/equipment/{id}/rack-position | PUT/DELETE position |
| /api/v1/dcim/pdus/ | PDUs |
| /api/v1/contracts/, /{id}/equipment | Contrats |
| /api/v1/software/, /{id}/licenses, /{id}/installations | Logiciels |
| /api/v1/network-ports/, /{id}/connect | Ports, connexions |
| /api/v1/attachments/, /api/v1/entities/ | Pièces jointes, entités |
| /api/v1/topology/physical | Topologie |
| /api/v1/tickets/, /{id}, /comments, /history, /assign, /resolve, /close, /reopen | Tickets |
| /api/v1/tickets/stats, /templates/, /from-template | Stats, modèles |
| /api/v1/notifications/, /count, /{id}/read, /read-all, /delete-read, /broadcast | Notifications |
| /api/v1/knowledge/categories, /articles, /{id}/feedback, /publish, /unpublish | KB |
| /api/v1/export/* | CSV (equipment, tickets, contracts, software, ip-addresses, audit-logs) |
| /api/v1/search/ | Recherche globale |
| /api/v1/webhooks/, /{id}, /test, /deliveries, /events | Webhooks |
| /api/v1/settings/, /by-category, /{key}, /test-smtp | Paramètres système (superadmin) |

## Troubleshooting

- **DB** : `docker-compose logs db`, .env
- **Worker** : `docker-compose logs worker`, Redis
- **401** : token expiré, re-login
- **429** : rate limit, attendre
- **Sandbox** : `docker build -t inframate-sandbox:latest -f docker/sandbox.Dockerfile .`
- **macOS ARM64** : WinRM non dispo (SSH ok)
- **468 / style.css / écran blanc** : Le code HTTP 468 est non standard (souvent proxy/WAF/antivirus, ex. Symantec). L’app charge `style.css` en non-bloquant et applique un style de secours dans `index.html` ; l’écran blanc ne devrait plus se produire. Si le 468 persiste : tester en navigateur externe ou sans proxy d’entreprise, et vérifier les règles du proxy/firewall.
