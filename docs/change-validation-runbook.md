# Runbook · Capture et validation post-changement IOS

Ce runbook complète les collecteurs du dépôt. Il aide à organiser une capture comparable avant et après une intervention, sans exposer de données de production dans Git.

## Avant la fenêtre

- Valider le périmètre, le créneau, le chemin d'escalade et le seuil de retour arrière.
- Vérifier l'accès SSH et la clé d'hôte du ou des équipements concernés.
- Conserver les exports dans un répertoire local restreint, hors du dépôt.
- Créer un dossier de preuve avec l'heure UTC et l'identifiant de changement.

Exemple de capture hors ligne avec les fixtures incluses :

```bash
mkdir -p out/change-2026-11-13
python -m programs.change_validation capture \
  --fixture examples/before \
  --output out/change-2026-11-13/before.json
```

Pour une capture réelle, utilise un compte à privilèges minimaux et renseigne explicitement l'hôte, la clé et le fichier de sortie. Contrôle l'empreinte SSH avant la première connexion.

## Pendant le changement

1. Noter l'heure de début réelle et l'état des services concernés.
2. Exécuter la modification approuvée.
3. Ne pas conclure sur un simple lien physique : vérifier voisins, VLAN autorisés, table de routage et flux applicatifs convenus.
4. En cas d'écart, appliquer le seuil Go/No-Go défini par le changement ; ne pas improviser un rollback non validé.

## Après la fenêtre

```bash
python -m programs.change_validation capture \
  --fixture examples/after \
  --output out/change-2026-11-13/after.json

python -m programs.change_validation compare \
  --before out/change-2026-11-13/before.json \
  --after out/change-2026-11-13/after.json \
  --expected examples/expected-change.json \
  --output out/change-2026-11-13/changes.html
```

Lis d'abord les changements inattendus et les vérifications indisponibles. Un rapport sans écart ne remplace pas les critères de service métier ou les tests de bout en bout.

## Clôture

Conserve le rapport et les décisions dans l'espace d'exploitation approuvé. Ne publie dans Git que des exemples assainis : adresses de documentation, noms génériques et secrets supprimés.
