# Plugin Domoticz Link-Tap — Documentation française

## Présentation

[Link-Tap](https://www.link-tap.com/) est un système d'arrosage sans fil piloté via un service cloud. Ce plugin Domoticz connecte votre installation Link-Tap à [Domoticz](https://www.domoticz.com) via l'API REST officielle Link-Tap, vous permettant de surveiller et contrôler votre arrosage directement depuis votre système domotique.

---

## Fonctionnalités

- Lecture en temps réel du débit instantané et du volume cumulé pendant les cycles d'arrosage
- Contrôle du mode d'arrosage (Intervalles, Pair/Impair, Sept jours, Mensuel)
- Démarrage et arrêt immédiats de l'arrosage en mode instantané
- Affichage des alertes matérielles (détection de chute, manque d'eau, fuite, obstruction, valve défectueuse)
- Remontée du niveau de batterie et de la puissance du signal pour chaque dispositif
- Vérification automatique des nouvelles versions sur la page de releases GitHub
- **Interface bilingue** : les messages du journal et les chaînes de statut suivent la langue configurée dans Domoticz (anglais et français inclus ; d'autres langues peuvent être ajoutées facilement)

---

## Prérequis

- Domoticz avec le support des plugins Python activé
- Un compte Link-Tap avec au moins une passerelle (Gateway) et un Taplinker
- Une clé API générée sur la [page développeur Link-Tap](https://www.link-tap.com/#!/api-for-developers)
- La bibliothèque Python `requests` (généralement déjà présente sur les hôtes Domoticz)

---

## Installation

1. Clonez ou téléchargez ce dépôt dans le répertoire des plugins de Domoticz :
   ```
   cd /opt/domoticz/plugins          # adaptez le chemin à votre installation
   git clone https://github.com/DebugBill/Link-Tap
   ```
2. Redémarrez Domoticz.
3. Allez dans **Configuration → Matériel**, cliquez sur **Ajouter** et sélectionnez **Link-Tap Watering System** dans la liste déroulante.

---

## Configuration

| Paramètre | Description |
|-----------|-------------|
| **User** | Votre nom d'utilisateur Link-Tap (adresse e-mail) |
| **Key** | Votre clé API Link-Tap |
| **Retour au mode précédent après le mode manuel** | Si `True`, le contrôleur revient au programme planifié à la fin d'une session d'arrosage manuel |
| **Durée maximale d'arrosage (sec)** | Coupure de sécurité appliquée lors du démarrage manuel (1–1439 s, défaut 1439) |
| **Niveau de débogage** | Verbosité des messages dans le journal Domoticz (laisser sur *None* en utilisation normale) |

---

## Dispositifs créés

Cinq dispositifs Domoticz sont créés automatiquement pour **chaque Taplinker** trouvé sur votre compte (dans la limite des 255 dispositifs par matériel imposée par Domoticz) :

| Dispositif | Type | Description |
|------------|------|-------------|
| **Flow** | Capteur personnalisé | Débit instantané en l/min pendant l'arrosage |
| **Volume** | Capteur personnalisé | Volume cumulé (litres) pour la session d'arrosage en cours |
| **Watering Modes** | Sélecteur | Active un programme planifié : Intervalles / Pair-Impair / Sept jours / Mensuel |
| **Status** | Alerte | Vert au repos, Rouge en cas de défaut matériel (voir liste ci-dessous) |
| **On/Off** | Interrupteur | Démarre ou arrête l'arrosage immédiatement en mode instantané |

### Conditions d'alerte remontées sur le dispositif Status

- Chute détectée (dispositif renversé)
- Manque d'eau
- Fuite détectée
- Obstruction du tuyau
- Valve défectueuse

---

## Fréquence des mises à jour

| Donnée | Intervalle |
|--------|------------|
| Statut d'arrosage (débit, volume, synchronisation On/Off) | 30 secondes |
| Rafraîchissement de la liste des dispositifs (détection de nouveau matériel) | 5 minutes |
| Vérification de version (GitHub) | 2 heures |

> Link-Tap applique une limitation de débit sur son API. Ne réduisez pas l'intervalle de heartbeat en dessous de 15 secondes.

---

## Vérification automatique de version

Toutes les deux heures, le plugin interroge la [page des releases GitHub](https://github.com/DebugBill/Link-Tap/releases/latest) et compare le dernier tag publié avec la version en cours d'exécution par **comparaison numérique** (ex. `2.1 > 2.00 > 0.2`) :

| Situation | Niveau | Message |
|-----------|--------|---------|
| GitHub propose une version plus récente | `Error` | Notification de mise à jour disponible |
| Version locale égale à la dernière release | `Log` | À jour |
| Version locale en avance sur la dernière release | `Log` | Notification de version de développement (pas d'alerte) |

Le cas « en avance » est intentionnel : en cours de développement, le plugin peut porter un numéro de version non encore publié sur GitHub, ce qui ne doit pas générer une fausse alerte de mise à jour.

---

## Ajouter une nouvelle langue

Toutes les chaînes visibles par l'utilisateur sont stockées dans le dictionnaire `STRINGS` en haut de `plugin.py`. Pour ajouter une langue :

1. Copiez l'intégralité du bloc `'en'`.
2. Changez la clé pour le code ISO 639-1 de votre langue (ex. `'de'` pour l'allemand).
3. Traduisez chaque chaîne. Conservez les `{balises}` identiques — elles sont remplies à l'exécution.
4. Le plugin sélectionne automatiquement la langue configurée dans Domoticz (`Configuration → Paramètres → Langue`). L'anglais est utilisé en secours pour toute clé manquante.

---

## Historique des versions

| Version | Date | Notes |
|---------|------|-------|
| 2.00 | 2026 | Corrections de bugs (condition booléenne, code mort, type `autoBack`, gestion des erreurs HTTP), support bilingue EN/FR, refactorisation du code, comparaison numérique des versions (pas de fausse alerte lors du développement d'une évolution) |
| 0.2 | Mai 2024 | Meilleure gestion des mises à jour des dispositifs de statut |
| 0.1 | Juin 2021 | Version initiale |

---

## Limitations connues

- Le plugin interroge l'API cloud Link-Tap. Une connexion internet active est requise en permanence.
- Domoticz limite les entrées matérielles à 255 dispositifs. Avec de nombreux Taplinkers (> 51), plusieurs entrées matérielles seraient nécessaires — ce cas n'est pas géré automatiquement pour l'instant.

---

## Auteur

**DebugBill** — <DebugBill@thauvin.org>

## Licence

Ce projet est distribué sous la licence **GNU General Public License v3.0 (GPL-3.0)**.
Vous êtes libre de l'utiliser, le modifier et le redistribuer dans le respect de cette licence.
Voir [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html) pour le texte complet.
