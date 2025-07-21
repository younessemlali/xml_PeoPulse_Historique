# 📄 PeoPulse XML Historique Manager

Application Streamlit pour l'ajout automatique de la balise `<HISTORIQUE>` dans les fichiers XML de contrats de travail pour la plateforme PeoPulse.

## 🎯 Problématique

L'ERP actuel ne génère pas automatiquement la balise `<HISTORIQUE>` nécessaire pour l'historisation des contrats sur PeoPulse. Cette application automatise l'ajout de cette balise, évitant ainsi le traitement manuel fastidieux.

## ✨ Fonctionnalités

- 📤 **Chargement multiple** : Traitement de plusieurs fichiers XML simultanément
- 🔍 **Analyse automatique** : Détection des contrats via la balise `<CONO_TXT>`
- 📊 **Visualisation** : Tableau récapitulatif des contrats nécessitant modification
- 🎯 **Traitement flexible** : 
  - Mode batch (tous les contrats)
  - Mode sélectif (contrat par contrat)
- 💾 **Export pratique** :
  - Téléchargement individuel des fichiers
  - Export groupé en ZIP

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation locale

1. Cloner le repository
```bash
git clone https://github.com/[votre-username]/peopulse-xml-historique.git
cd peopulse-xml-historique
```

2. Installer les dépendances
```bash
pip install -r requirements.txt
```

3. Lancer l'application
```bash
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

## 🌐 Déploiement sur Streamlit Cloud

1. Forkez ce repository sur votre compte GitHub
2. Connectez-vous à [Streamlit Cloud](https://streamlit.io/cloud)
3. Cliquez sur "New app"
4. Sélectionnez votre repository et la branche principale
5. Définissez `app.py` comme fichier principal
6. Cliquez sur "Deploy"

## 📖 Guide d'utilisation

### 1. Chargement des fichiers
- Cliquez sur "Browse files" ou glissez-déposez vos fichiers XML
- Plusieurs fichiers peuvent être traités simultanément

### 2. Analyse des contrats
L'application affiche pour chaque fichier :
- Le numéro de contrat (`<CONO_TXT>`)
- La présence ou absence de la balise `<HISTORIQUE>`
- L'action requise

### 3. Traitement
Deux modes disponibles :
- **Traitement en masse** : Ajoute la balise à tous les contrats qui n'en ont pas
- **Traitement sélectif** : Choisissez individuellement les contrats à modifier

### 4. Téléchargement
- Les fichiers modifiés sont préfixés avec "modified_"
- Option de téléchargement individuel ou groupé (ZIP)

## 📋 Structure XML

La balise `<HISTORIQUE>1</HISTORIQUE>` est insérée automatiquement entre :

```xml
<STATUT_SALARIE>0</STATUT_SALARIE>
<HISTORIQUE>1</HISTORIQUE>  <!-- Balise ajoutée -->
<CONTDET_1>
    ...
</CONTDET_1>
```

## 🔧 Configuration

L'application utilise les paramètres suivants :
- **Valeur de la balise** : Toujours "1"
- **Position** : Après `<STATUT_SALARIE>`, avant `<CONTDET_1>`
- **Encodage** : UTF-8

## 🐛 Dépannage

### Erreur de parsing XML
- Vérifiez que vos fichiers XML sont bien formés
- L'application gère automatiquement l'encodage UTF-8

### Balise non ajoutée
- Vérifiez que la structure contient bien `<STATUT_SALARIE>`
- Assurez-vous que le contrat est correctement identifié via `<CONO_TXT>`

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche (`git checkout -b feature/amelioration`)
3. Commit vos changements (`git commit -m 'Ajout de fonctionnalité'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👥 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur GitHub.

---

Développé avec ❤️ pour simplifier la gestion des contrats PeoPulse
