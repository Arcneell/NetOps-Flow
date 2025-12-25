# NetOps-Flow

Plateforme de gestion des opérations réseau auto-hébergée, entièrement générée par IA (Claude).

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

- **Backend**: FastAPI 0.109 + Python 3.11 + SQLAlchemy 2.0 + Celery 5.3
- **Frontend**: Vue.js 3 + Pinia + PrimeVue 3.46 + TailwindCSS 3.4
- **Base de données**: PostgreSQL 15 + Redis 7
- **Containerisation**: Docker + Docker Compose

## Architecture

```
frontend/          # Vue.js 3 SPA
├── src/
│   ├── components/shared/   # Composants réutilisables (StatusTag avec gradients)
│   ├── stores/              # Pinia stores (auth, ui, dcim, contracts, software, networkPorts, attachments)
│   ├── views/               # Pages principales
│   ├── i18n/                # Traductions EN/FR
│   ├── api.js               # Client Axios
│   ├── router.js            # Routes avec guards de permissions
│   └── style.css            # Design System Modern Slate (Anthracite, Zinc, Bleu électrique)

backend/           # FastAPI API
├── core/
│   ├── config.py           # Configuration Pydantic Settings
│   ├── database.py         # SQLAlchemy engine + sessions
│   ├── security.py         # JWT, bcrypt, Fernet encryption, TOTP (pyotp)
│   ├── rate_limiter.py     # Rate limiting Redis
│   └── logging.py          # Logging structuré JSON/Text
├── routers/
│   ├── auth.py             # POST /token, GET /me, MFA endpoints (/verify-mfa, /mfa/setup, /mfa/enable-with-secret, /mfa/disable)
│   ├── users.py            # CRUD utilisateurs (admin)
│   ├── ipam.py             # Subnets, IPs, scan nmap
│   ├── topology.py         # Données visualisation réseau + topologie physique
│   ├── scripts.py          # Upload, exécution scripts
│   ├── inventory.py        # Équipements, fabricants, fournisseurs (avec isolation entity_id)
│   ├── dashboard.py        # Statistiques
│   ├── dcim.py             # Gestion Racks et PDUs (optimisé avec joinedload)
│   ├── contracts.py        # Contrats de maintenance/assurance
│   ├── software.py         # Catalogue logiciels et licences
│   ├── network_ports.py    # Ports réseau et connexions physiques
│   ├── attachments.py      # Pièces jointes (documents)
│   └── entities.py         # Entités multi-tenant
├── models.py               # Modèles SQLAlchemy
├── schemas.py              # Schémas Pydantic
└── app.py                  # Application FastAPI

worker/            # Celery worker
└── tasks.py       # Tâches async (exécution scripts, scan subnet, alertes expirations, collecte logiciels)
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

## Sécurité

- **Auth**: JWT (8h expiration) + bcrypt pour mots de passe
- **MFA/TOTP**: Authentification à deux facteurs optionnelle avec pyotp (secrets chiffrés en base avec Fernet)
- **Encryption**: Fernet pour données sensibles (remote passwords, TOTP secrets)
- **Rate Limiting**: Redis-backed, 5 req/60s sur login
- **RBAC**: Rôles admin/user + permissions granulaires (ipam, scripts, inventory, topology, settings)
- **Sandbox Docker**: Mémoire 256MB, CPU 0.5, network disabled, read-only filesystem
- **Audit Log**: Traçabilité complète des événements MFA (LOGIN_FAILED, MFA_CHALLENGE, MFA_SUCCESS, MFA_FAILED, MFA_ENABLED, MFA_DISABLED)

## Commandes

```bash
# Démarrage
docker-compose up --build

# Logs
docker-compose logs -f backend
docker-compose logs -f worker

# Migrations
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"

# Base de données
docker-compose exec db psql -U netops netops_flow
```

## URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Variables d'Environnement Clés

| Variable | Défaut | Description |
|----------|--------|-------------|
| POSTGRES_PASSWORD | netopspassword | Mot de passe PostgreSQL |
| JWT_SECRET_KEY | (généré) | Clé secrète JWT |
| ENCRYPTION_KEY | (généré) | Clé Fernet |
| ALLOWED_ORIGINS | http://localhost:3000 | CORS origins |
| LOG_LEVEL | INFO | Niveau de log |
| DOCKER_SANDBOX_MEMORY | 256m | Limite mémoire sandbox |
| SCRIPT_EXECUTION_TIMEOUT | 300 | Timeout scripts (sec) |

## Credentials par Défaut

- **Admin**: admin / admin (MFA désactivé par défaut)
- **Database**: netops / netopspassword / netops_flow

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
  - Namespaces: `common`, `nav`, `auth`, `dashboard`, `ipam`, `inventory`, `scripts`, `settings`, `users`, `validation`, `messages`, `filters`, `status`, `ip`, `remote`, `dcim`, `contracts`, `software`, `entities`

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
- `users` - Utilisateurs avec rôles, permissions et MFA (colonnes: mfa_enabled, totp_secret chiffré)
- `entities` - Entités multi-tenant
- `subnets` / `ip_addresses` - IPAM
- `scripts` / `script_executions` - Automatisation
- `manufacturers` / `equipment_types` / `equipment_models` - Catalogue
- `locations` / `suppliers` / `equipment` - Inventaire
- `racks` / `pdus` - DCIM
- `contracts` / `contract_equipment` - Contrats
- `software` / `software_licenses` / `software_installations` - Logiciels
- `network_ports` - Ports réseau et connexions
- `attachments` - Pièces jointes

## API Endpoints Principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| /api/v1/auth/token | POST | Login, obtenir JWT ou challenge MFA |
| /api/v1/auth/verify-mfa | POST | Vérifier code TOTP et obtenir JWT |
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

## Troubleshooting

**Connexion DB échoue**: Vérifier `docker-compose logs db`, credentials .env

**Worker ne traite pas les tâches**: `docker-compose logs worker`, vérifier Redis

**401 Unauthorized**: Token expiré, re-login

**429 Too Many Requests**: Rate limited, attendre 60 secondes

**Sandbox Docker indisponible**: Rebuild image `docker build -t netops-sandbox:latest -f docker/sandbox.Dockerfile .`

**Build échoue sur macOS (Apple Silicon)**: PowerShell n'est installé que sur AMD64. Sur ARM64, l'exécution distante via WinRM ne sera pas disponible en développement (SSH reste fonctionnel)
