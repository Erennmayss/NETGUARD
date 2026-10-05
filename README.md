 NETGUARD - Plateforme d'Administration Réseau, Segmentation VLAN & Détection d'Intrusions (IDS)
 **NETGUARD** est une solution intégrée de cybersécurité et d'automatisation réseau développée par une équipe de **4 étudiants dans le cadre d'un projet de 4ème année d'études supérieures, associé à un stage pratique au sein de Sonatrach**.
Elle combine un **Système de Détection d'Intrusions (IDS Snort)** en temps réel, un moteur d'**automatisation d'équipements Cisco (VLAN, Port-Security, TFTP Backup via Nornir/Netmiko)** et un **tableau de bord web moderne (Flask & HTML5/CSS3/JS)**.
> 📄 **Note sur le Rapport Détaillé** :  
> Le **rapport officiel complet** (comprenant l'architecture réseau, la sécurité, la méthodologie de test et l'analyse théorique et pratique) est disponible directement dans le dépôt sous le nom de [RapportNetGuard (5).pdf](ids_1/NetWeb/docs/RapportNetGuard%20(5).pdf).
---
## 🚀 Description Courte (Pour la section "About" de GitHub)
```text
NETGUARD est une plateforme web d'administration réseau et de cybersécurité centralisée combinant l'automatisation d'équipements Cisco (VLANs, Port-Security, sauvegardes TFTP via Nornir), la surveillance de trafic et la détection d'intrusions Snort avec alertes temps réel (Email/Windows Toast). Projet de 4ème année réalisé par une équipe de 4 étudiants lors d'un stage chez Sonatrach. 📄 Pour plus de détails, consultez le rapport disponible dans ids_1/NetWeb/docs/RapportNetGuard (5).pdf.

  

  
📋 Table des Matières

  

  
✨ Fonctionnalités Principales

  
📐 Architecture du Système

  
🛠️ Stack Technique

  
📁 Arborescence du Projet

  
⚡ Installation & Démarrage Rapide

  
🔐 Authentification & Rôles

  
👥 Équipe & Remerciements

  
📑 Rapport & Documentation Complète

  

  

  
✨ Fonctionnalités Principales

  
🔒 1. Détection d'Intrusions & Alertes Temps Réel (IDS Snort)

  

  
Sonde Snort IDS : Surveillance du trafic réseau et détection instantanée des attaques (SQL Injection, Scans de ports, tentative d'exploit RPC, etc.).

  
Moteur de Notifications Instantanées : Envoi automatique d'alertes par Email SMTP (Gmail) et notifications Windows Toast.

  
Base de Données Centralisée : Historisation et tri des alertes par sévérité (Critical, High, Medium, Low) sur Supabase / PostgreSQL.

  

  
🌐 2. Automatisation Réseau Cisco & Segmentation VLAN

  

  
Gestion Dynamique des VLANs : Création, modification et suppression de VLANs avec synchronisation en temps réel des ports commutateurs (Gi1/0/1, Gi1/0/2, etc.).

  
Configuration d'Interfaces & Sécurité : Attribution des modes Access/Trunk et verrouillage des adresses MAC statiques (Port-Security).

  
Sauvegarde & Restauration TFTP : Export/Import à distance des configurations Cisco (running-config et startup-config).

  
Synchronisation BDD ↔ Switch : Maintien de l'état réel des cartes réseaux et des VLANs entre les équipements physiques et la BDD.

  

  
📊 3. Tableau de Bord Web & Monitoring

  

  
Interface Réactive & Dynamic UI : Dashboard moderne en Thème Sombre (Dark Mode) avec graphiques de trafic.

  
Gestion des Équipements & Logs : Inventaire complet des switches, suivi des états de connexion et accès aux journaux d'événements.

  
Scripts d'Automatisation : Exécution contrôlée de tâches batch et scripts de maintenance.

  

  
🔑 4. Sécurité & Contrôle d'Accès (RBAC)

  

  
Authentification JWT : Protection des endpoints API par jetons de session (Flask-JWT-Extended).

  
Gestion des Rôles (RBAC) : Droits d'accès granulaires pour Admin, Network Admin, Security Admin et Viewer.

  
Connexions Sécurisées : SSL/TLS activé pour PostgreSQL / Supabase et requêtes SSH chiffrées pour Nornir.

  

  

  
📐 Architecture du Système

  

  

  
🛠️ Stack Technique

  

  
Langages : Python 3.10+, JavaScript (ES6+), HTML5, CSS3.

  
Backend API : Flask, Waitress WSGI, Flask-JWT-Extended, Flask-CORS.

  
Automation Réseau : Nornir 3.x, Netmiko, PyYAML.

  
Base de Données : Supabase / PostgreSQL, psycopg2-binary.

  
Cybersécurité : Snort IDS, win10toast (Windows Notifications), SMTP Gmail.

  
Frontend : CSS Grid/Flexbox (Custom Dark Theme), Vanilla JS, React Standalone Components.

  

  

  
📁 Arborescence du Projet

  
text
NETGUARD/
├── ids_1/
│   └── NetWeb/
│       ├── docs/
│       │   └── RapportNetGuard (5).pdf  # 📄 Rapport officiel complet du projet
│       ├── Backend/
│       │   ├── app.py                   # Point d'entrée principal Flask
│       │   ├── serve.py                 # Serveur de production Waitress
│       │   ├── dashboard_api.py         # Endpoints pour les statistiques et métriques
│       │   ├── equipements_api.py       # Endpoints de gestion des switches
│       │   ├── network_api.py           # Automation Cisco, Nornir & sauvegardes TFTP
│       │   ├── notifier_advanced.py     # Service d'envoi de notifications (Mail/Toast)
│       │   ├── snort_alert_processor.py # Traitement des alertes Snort
│       │   ├── requirements.txt         # Dépendances du projet
│       │   ├── Database/                # Modèles BDD (alerts, vlan, interface, traffic, etc.)
│       │   └── Snort/                   # Modules d'intégration Snort IDS
│       └── Frontend/
│           ├── index.html / login.html  # Page de connexion
│           ├── dashboard.html           # Vue d'ensemble du système
│           ├── alerts.html              # Suivi des incidents et alertes IDS
│           ├── vlan.html                # Configuration des VLANs
│           ├── interfaces.html          # Gestion des ports & Port-Security
│           ├── equipements.html         # Inventaire du parc réseau
│           ├── traffic.html             # Analyseur de trafic
│           └── auth.js / sidebar.js     # Logique JS & Interface UI
└── README.md                            # Présentation du projet (Ce fichier)

  

  
⚡ Installation & Démarrage Rapide

  
1. Prérequis

  

  
Python 3.10 ou supérieur installé.

  
Une base de données Supabase ou PostgreSQL accessible.

  
Une sonde Snort IDS (optionnel pour les tests locaux).

  

  
2. Cloner le Dépôt

  
bash
git clone https://github.com/Erennmayss/NETGUARD.git
cd NETGUARD

  
3. Configurer l'Environnement Virtuel & Dépendances

  
bash
cd ids_1/NetWeb/Backend
# Création de l'environnement virtuel
python -m venv venv
# Activation (Windows)
.\venv\Scripts\activate
# Activation (Linux/macOS)
source venv/bin/activate
# Installation des paquets
pip install -r requirements.txt

  
4. Configuration des Variables d'Environnement (.env)

  

Créez un fichier .env dans le dossier Backend/ :


  
env
DATABASE_URL=postgresql://postgres.user:password@db.supabase.co:5432/postgres
JWT_SECRET_KEY=votre_cle_secrete_jwt
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
APP_HOST=0.0.0.0
APP_PORT=5000
WAITRESS_THREADS=4

  
5. Démarrer l'Application

  
Mode Développement :

  
bash
python app.py

  
Mode Production (Waitress WSGI) :

  
bash
python serve.py

  

Rendez-vous sur http://localhost:5000 sur votre navigateur.


  

  
🔐 Authentification & Rôles

  

Le système implémente un contrôle d'accès basé sur les rôles (RBAC) :


  

  
admin : Accès global et gestion des utilisateurs, des accès et de la plateforme.

  
network_admin : Administration des équipements réseau, configuration des VLANs, gestion des ports et sauvegardes TFTP.

  
security_admin : Gestion et suivi des alertes IDS Snort, règles de détection et notifications d'incidents.

  
viewer : Accès en lecture seule aux métriques du dashboard, état du réseau et logs.

  

  

  
👥 Équipe & Remerciements

  

Projet réalisé par une équipe de 4 étudiants de 4ème année (@Erennmayss
) dans le cadre d'un stage au sein de l'entreprise SONATRACH :


  

  
Équipe de 4 Étudiants (Architecture Système, Backend Flask, IDS Snort & Automation Nornir).

  
Encadrement & Remerciements : Un grand merci aux équipes et encadrants de Sonatrach pour leur accompagnement technique et les ressources réseau fournies lors du stage.

  

  

  
📑 Rapport & Documentation Complète

  

Pour consulter le rapport officiel complet de stage et la documentation détaillée :


  

  
📄 Rapport Officiel PDF : ids_1/NetWeb/docs/RapportNetGuard (5).pdf
