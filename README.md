# team-du-mardi-ai-agent-project

Un agent de voyage intelligent capable d'organiser des séjours complets en synchronisant vols, hébergements et activités disponibles.

## Description

Ce projet est un agent de planification de voyage basé sur FastAPI. Il automatise la recherche et l'organisation de séjours en effectuant les tâches suivantes :

* Recherche de données : Extraction d'informations sur les vols, les hôtels et les activités via des outils (APIs).

* Validation logistique : Vérification de la cohérence entre les horaires (ex: correspondance entre l'arrivée d'un vol et l'ouverture du check-in).

* Planification : Génération d'un itinéraire structuré jour par jour.

## Getting Started

### Dépendances

* Python: 3.12
* FastAPI

## Installation et Environnement Virtuel

### 1. Création de l'environnement
Ouvrez votre terminal à la racine du projet :

```bash
python -m venv venv
```

### 2. Activation de l'environnement 

Pour Windows : 
```bash
venv\Scripts\activate
```
Pour MacOS / Linux : 
```bash
source venv/bin/activate
```

### 3. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 4. Désactivation
```bash
deactivate
```

### 5. Exécuter l'agent 
```bash
adk run my_agent
```

## Fonctionnalités à venir

- [ ] Intégration d'une interface Frontend (React/Vue)

## Help

## Authors

Contributors names and contact info

ex. Dominique Pizzie  
ex. [@DomPizzie](https://twitter.com/dompizzie)

## Version History

* 0.2
    *
* 0.1
    * Initial Release