# NETGUARD - Plateforme d'Administration Réseau, Segmentation VLAN & Détection d'Intrusions (IDS)

**NETGUARD** est une solution intégrée de cybersécurité et d'automatisation réseau développée par une équipe de **4 étudiants dans le cadre d'un projet de 4ème année d'études supérieures, associé à un stage pratique au sein de Sonatrach**.

Elle combine un **Système de Détection d'Intrusions (IDS Snort)** en temps réel, un moteur d'**automatisation d'équipements Cisco (VLAN, Port-Security, TFTP Backup via Nornir/Netmiko)** et un **tableau de bord web (Flask, HTML5, CSS3 et JavaScript)**.

> **Note sur le rapport détaillé :**
> Le **rapport officiel complet**, comprenant l'architecture réseau, la sécurité, la méthodologie de test ainsi que l'analyse théorique et pratique, est disponible dans le dépôt :
> `ids_1/NetWeb/docs/RapportNetGuard (5).pdf`

---

## Description courte

NETGUARD est une plateforme web d'administration réseau et de cybersécurité centralisée combinant l'automatisation d'équipements Cisco (VLAN, Port-Security, sauvegardes TFTP via Nornir), la surveillance du trafic et la détection d'intrusions Snort avec alertes en temps réel (Email/Windows Toast).

Projet de 4ème année réalisé par une équipe de 4 étudiants lors d'un stage au sein de Sonatrach.

Pour plus de détails, consultez le rapport disponible dans `ids_1/NetWeb/docs/RapportNetGuard (5).pdf`.

---

## Table des matières

* [Fonctionnalités principales](#fonctionnalités-principales)
* [Architecture du système](#architecture-du-système)
* [Stack technique](#stack-technique)
* [Arborescence du projet](#arborescence-du-projet)
* [Installation et démarrage rapide](#installation-et-démarrage-rapide)
* [Authentification et rôles](#authentification-et-rôles)
* [Équipe et remerciements](#équipe-et-remerciements)
* [Rapport et documentation complète](#rapport-et-documentation-complète)

---

## Fonctionnalités principales

### 1. Détection d'intrusions et alertes en temps réel

* **Sonde Snort IDS :** surveillance du trafic réseau et détection des attaques telles que les injections SQL, les scans de ports et les tentatives d'exploitation RPC.
* **Notifications instantanées :** envoi automatique d'alertes par Email SMTP (Gmail) et notifications Windows Toast.
* **Base de données centralisée :** historisation et tri des alertes par niveau de sévérité (Critical, High, Medium, Low) sur Supabase/PostgreSQL.

### 2. Automatisation réseau Cisco et segmentation VLAN

* **Gestion dynamique des VLAN :** création, modification et suppression de VLAN avec synchronisation des ports des commutateurs.
* **Configuration des interfaces et sécurité :** attribution des modes Access/Trunk et verrouillage des adresses MAC statiques avec Port-Security.
* **Sauvegarde et restauration TFTP :** export et import à distance des configurations Cisco (`running-config` et `startup-config`).
* **Synchronisation BDD ↔ Switch :** maintien de la cohérence entre l'état réel des équipements réseau et les informations enregistrées dans la base de données.

### 3. Tableau de bord web et monitoring

* **Interface web réactive :** dashboard moderne avec thème sombre et visualisation des données réseau.
* **Gestion des équipements et des logs :** inventaire des switches, suivi des états de connexion et consultation des journaux d'événements.
* **Scripts d'automatisation :** exécution contrôlée de tâches batch et de scripts de maintenance.

### 4. Sécurité et contrôle d'accès (RBAC)

* **Authentification JWT :** protection des endpoints API à l'aide de jetons via Flask-JWT-Extended.
* **Gestion des rôles (RBAC) :** droits d'accès différenciés pour les rôles Admin, Network Admin, Security Admin et Viewer.
* **Connexions sécurisées :** utilisation de SSL/TLS pour PostgreSQL/Supabase et de connexions SSH chiffrées pour l'automatisation réseau avec Nornir/Netmiko.

---

## Architecture du système

L'architecture de NETGUARD repose sur trois principaux composants :

1. **Frontend :** interface web permettant aux utilisateurs de consulter les informations réseau, les alertes IDS et de gérer les équipements.
2. **Backend :** API Flask assurant la logique métier, l'authentification, l'automatisation réseau et la communication avec la base de données.
3. **Infrastructure réseau et sécurité :** équipements Cisco, système Snort IDS et base de données PostgreSQL/Supabase.

---

## Stack technique

| Composant             | Technologies                                         |
| --------------------- | ---------------------------------------------------- |
| Langages              | Python 3.10+, JavaScript ES6+, HTML5, CSS3           |
| Backend               | Flask, Waitress WSGI, Flask-JWT-Extended, Flask-CORS |
| Automatisation réseau | Nornir 3.x, Netmiko, PyYAML                          |
| Base de données       | Supabase, PostgreSQL, psycopg2-binary                |
| Cybersécurité         | Snort IDS, SMTP Gmail, win10toast                    |
| Frontend              | HTML5, CSS3, JavaScript, CSS Grid/Flexbox            |
| Serveur               | Waitress WSGI                                        |

---

## Arborescence du projet

```text
NETGUARD/
├── ids_1/
│   └── NetWeb/
│       ├── docs/
│       │   └── RapportNetGuard (5).pdf
│       ├── Backend/
│       │   ├── app.py
│       │   ├── serve.py
│       │   ├── dashboard_api.py
│       │   ├── equipements_api.py
│       │   ├── network_api.py
│       │   ├── notifier_advanced.py
│       │   ├── snort_alert_processor.py
│       │   ├── requirements.txt
│       │   ├── Database/
│       │   └── Snort/
│       └── Frontend/
│           ├── index.html
│           ├── login.html
│           ├── dashboard.html
│           ├── alerts.html
│           ├── vlan.html
│           ├── interfaces.html
│           ├── equipements.html
│           ├── traffic.html
│           ├── auth.js
│           └── sidebar.js
└── README.md
```

---

## Installation et démarrage rapide

### 1. Prérequis

* Python 3.10 ou supérieur
* Une base de données Supabase ou PostgreSQL accessible
* Une sonde Snort IDS pour les tests liés à la détection d'intrusions

### 2. Cloner le dépôt

```bash
git clone https://github.com/Erennmayss/NETGUARD.git
cd NETGUARD
```

### 3. Configurer l'environnement virtuel et les dépendances

```bash
cd ids_1/NetWeb/Backend

# Création de l'environnement virtuel
python -m venv venv

# Activation sous Windows
.\venv\Scripts\activate

# Activation sous Linux/macOS
source venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement

Créer un fichier `.env` dans le dossier `Backend/` :

```env
DATABASE_URL=postgresql://postgres.user:password@db.supabase.co:5432/postgres
JWT_SECRET_KEY=votre_cle_secrete_jwt
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
APP_HOST=0.0.0.0
APP_PORT=5000
WAITRESS_THREADS=4
```

Les informations sensibles telles que les mots de passe, clés secrètes et identifiants de connexion ne doivent pas être publiées dans le dépôt GitHub.

### 5. Démarrer l'application

#### Mode développement

```bash
python app.py
```

#### Mode production avec Waitress

```bash
python serve.py
```

L'application est ensuite accessible à l'adresse :

```text
http://localhost:5000
```

---

## Authentification et rôles

NETGUARD implémente un contrôle d'accès basé sur les rôles (RBAC).

### Admin

Accès global à la plateforme, gestion des utilisateurs, des accès et des fonctionnalités d'administration.

### Network Admin

Administration des équipements réseau, configuration des VLAN, gestion des ports et sauvegardes TFTP.

### Security Admin

Gestion et suivi des alertes IDS Snort, règles de détection et notifications de sécurité.

### Viewer

Accès en lecture seule aux métriques du dashboard, à l'état du réseau et aux logs.

---

## Équipe et remerciements

Projet réalisé par une équipe de **4 étudiants de 4ème année** dans le cadre d'un stage au sein de l'entreprise **Sonatrach**.

L'équipe a travaillé notamment sur :

* Architecture du système
* Développement Backend Flask
* Développement Frontend
* Intégration et configuration de Snort IDS
* Automatisation réseau avec Nornir et Netmiko
* Gestion et sécurisation de la base de données

Nous remercions les équipes et les encadrants de Sonatrach pour leur accompagnement technique ainsi que pour les ressources réseau mises à disposition durant le stage.

---

## Rapport et documentation complète

Le rapport officiel contient notamment :

* L'architecture réseau
* L'architecture logicielle
* La configuration des équipements
* L'intégration de Snort IDS
* Les mécanismes de sécurité
* La segmentation VLAN
* L'automatisation réseau
* La méthodologie de test
* Les résultats et analyses
* La documentation théorique et pratique

Le rapport est disponible directement dans le dépôt :

```text
ids_1/NetWeb/docs/RapportNetGuard (5).pdf
```

---

## Licence

Projet académique réalisé dans le cadre d'un projet de 4ème année et d'un stage pratique au sein de Sonatrach.
