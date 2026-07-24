# Guide propriétaire FR — IaC Security Misconfiguration Scanner API

Ce document est le guide interne KazKN pour comprendre, tester et contrôler
l'Actor. Il complète le README public. La configuration Pay per event live a été
vérifiée le 2026-07-24; ses contrôles sont répétés à chaque release.

## 1. Le concept en clair

**IaC** veut dire **Infrastructure as Code**.

En français simple : au lieu de créer ton infrastructure cloud à la main dans
AWS, Google Cloud, Azure ou Kubernetes, les équipes décrivent cette
infrastructure dans des fichiers. Ces fichiers disent par exemple :

- crée un bucket S3 ;
- crée une base de données ;
- ouvre ou ferme un accès réseau ;
- chiffre ou ne chiffre pas un disque ;
- donne tel droit IAM à tel rôle ;
- déploie tel service Kubernetes.

L'Actor scanne ces fichiers avant le déploiement. Il ne se connecte pas au
compte cloud du client. Il lit seulement le code d'infrastructure fourni.

## 2. Ce que l'Actor fait

L'Actor prend une source IaC, lance Checkov 3.3.8 dessus, puis transforme le
résultat en sortie Apify propre. Le flux réel, dans son ordre exact, est :

1. **Étape 1 — validation :** il rejette les champs inconnus, les sources
   mélangées, les frameworks inconnus et les Check IDs incompatibles.
2. **Étape 2 — acquisition :** il télécharge une archive GitHub ou lit le record
   ZIP du Key-Value Store Apify. Il ne fait pas de `git clone`.
3. **Étape 3 — inspection :** il vérifie la taille et la structure du ZIP avant
   toute extraction : chemins, liens, types de fichiers, chiffrement, compression
   et expansion.
4. **Étape 4 — extraction :** il extrait uniquement des fichiers réguliers dans
   un dossier temporaire privé.
5. **Étape 5 — périmètre :** il choisit la racine demandée par `subdirectory`, si
   ce champ est présent.
6. **Étape 6 — scan :** il lance Checkov avec des arguments construits par
   l'Actor, les frameworks sélectionnés et éventuellement les `checkIds`.
7. **Étape 7 — normalisation :** il transforme seulement les champs autorisés en
   findings stables, calcule les totaux et le `gateDecision`.
8. **Étape 8 — nettoyage :** il quitte le workspace temporaire. Les sources et
   fichiers de scanner sont supprimés logiquement avant la livraison.
9. **Étape 9 — persistance :** il écrit les findings par lots dans le Dataset,
   puis écrit le résumé complet dans le record `OUTPUT`.
10. **Étape 10 — facturation :** seulement après persistance réussie, il tente
    exactement une charge `completed-scan`. Il ne retente jamais une charge
    ambiguë.

Ce que l'utilisateur achète : un scan automatisable qui répond à la question
« est-ce que ce snapshot IaC contient des mauvaises configurations de sécurité
connues par Checkov ? ».

### Où vit chaque étape dans le code

| Fichier | Rôle concret |
|---|---|
| `.actor/actor.json` | Déclare l'Actor, son image Docker et les schémas affichés par Apify. |
| `.actor/input_schema.json` | Construit le formulaire utilisateur dans la Console. |
| `.actor/output_schema.json` | Ajoute les liens Console vers `OUTPUT` et le Dataset. |
| `.actor/dataset_schema.json` | Décrit les colonnes publiques d'un finding. |
| `src/__main__.py` | Point d'entrée Python qui lance l'Actor. |
| `src/main.py` | Chef d'orchestre : validation, source, extraction, scan, persistance, facturation et statut final. |
| `src/input_model.py` | Valide chaque champ input et refuse les combinaisons dangereuses ou incohérentes. |
| `src/source.py` | Lit le ZIP Apify ou télécharge le snapshot GitHub autorisé sans exécuter le repo. |
| `src/archive.py`, `archive_format.py`, `archive_extract.py` | Inspectent puis extraient le ZIP avec les limites et protections de chemin. |
| `src/checkov_runner.py` | Construit et lance la commande Checkov 3.3.8 dans un environnement borné. |
| `src/checkov_catalog.json` | Catalogue versionné des politiques et catégories Checkov utilisées pour valider et enrichir les résultats. |
| `src/normalize.py` | Transforme la sortie brute Checkov en findings stables et en résumé `OUTPUT`. |
| `src/output.py` | Écrit les lignes Dataset et le record `OUTPUT` dans l'ordre sûr. |
| `src/billing.py` | Tente une seule charge `completed-scan` et échoue fermé si elle n'est pas confirmée. |
| `src/cleanup.py` | Contient les primitives de nettoyage utilisées pour ne pas laisser de source temporaire. |
| `Dockerfile` | Construit l'environnement cloud avec Python, Checkov et les outils IaC nécessaires. |
| `tests/` | Prouve les contrats fonctionnels, de sécurité, de sortie et de facturation. |

## 3. Ce que l'Actor ne fait pas

Limites importantes :

- il ne scanne pas un compte AWS/Azure/GCP vivant ;
- il ne corrige pas le code automatiquement ;
- il ne remplace pas un audit humain ;
- il ne cherche pas les secrets ;
- il ne scanne pas les dépendances applicatives ;
- il ne scanne pas les images Docker ;
- il ne donne pas une vraie sévérité exploitabilité ;
- il ne garantit pas une conformité SOC 2, PCI, NIST ou ISO.

La sortie `FAIL` veut seulement dire : au moins une politique Checkov a échoué.
Ce n'est pas un verdict juridique, compliance ou exploitabilité.

## 4. Lecture ligne par ligne des inputs

### `sourceType`

Choisit le type de source.

- `github` : l'Actor télécharge une archive GitHub.
- `zip_upload` : l'utilisateur upload un ZIP via le picker Apify.

Valeur par défaut : `github`. Une seule famille de source est permise par run.

### `repositoryUrl`

Utilisé seulement avec `sourceType = github`.

Exemple :

```json
"repositoryUrl": "https://github.com/hashicorp-education/learn-terraform-resources"
```

L'Actor accepte GitHub, pas n'importe quel hébergeur. Il ne clone pas le repo :
il télécharge une archive du snapshot demandé.

Format exact : `https://github.com/{owner}/{repository}`, sans credentials,
query string ni fragment. Le champ est obligatoire pour `github` et interdit pour
`zip_upload`.

### `repositoryRef`

Utilisé seulement avec GitHub.

Idéalement, c'est un commit SHA complet de 40 caractères. C'est important pour
reproduire exactement le même scan. Une branche ou un tag peut bouger.

Le champ est optionnel et limité à 128 caractères. Un SHA complet est une
recommandation de reproductibilité, pas une obligation technique.

### `subdirectory`

Optionnel.

Permet de scanner seulement un sous-dossier du repo ou du ZIP. Utile si le repo
contient plusieurs projets.

Il doit être un chemin POSIX relatif, comme `infra/production`, sans `/` initial,
`..`, backslash ou composant vide. Si le dossier n'existe pas, le run échoue de
façon sûre.

### `archiveFile`

Utilisé seulement avec `sourceType = zip_upload`.

Dans l'interface Apify, l'utilisateur sélectionne un ZIP. Apify stocke ce fichier
dans un Key-Value Store et fournit une URL interne de record. L'Actor lit cette
référence avec le client de stockage Apify authentifié. Il ne télécharge pas des
URLs arbitraires.

Le champ est obligatoire pour `zip_upload` et interdit pour `github`. La limite
compressée est 20 MiB.

### `githubToken`

Optionnel et secret.

Utilisé seulement pour un repo GitHub privé. Il doit avoir uniquement le droit de
lecture du contenu du repo cible. Il ne doit jamais être mis dans le nom d'une
Task, dans une URL, dans un webhook ou dans un fichier ZIP.

Il est interdit avec `zip_upload`. L'Actor ne le place ni dans les arguments du
scanner, ni dans le Dataset, ni dans `OUTPUT`.

### `frameworks`

Liste des frameworks IaC à scanner.

Exemples :

- `terraform`
- `kubernetes`
- `cloudformation`
- `helm`
- `kustomize`

Le choix impacte directement le temps de scan et le nombre de règles lancées.
La liste doit contenir entre 1 et 20 valeurs uniques. La valeur par défaut couvre
Terraform, CloudFormation, Kubernetes, Helm, Dockerfile et GitHub Actions. La
liste exhaustive et ses libellés Console vivent dans le README.

### `policyProfile`

Choisit le profil de politiques.

- `security` : profil par défaut, orienté mauvaises configurations sécurité.
- `all_iac` : lance aussi les politiques Checkov plus larges, y compris des
  conventions et bonnes pratiques non strictement cyber.

Pour vendre proprement l'Actor, le profil `security` doit être mis en avant.

### `checkIds`

Optionnel.

Permet de lancer seulement certains IDs Checkov. Exemple :

```json
"checkIds": ["CKV_AWS_20"]
```

Si `checkIds` est vide, l'Actor lance toutes les politiques compatibles avec les
frameworks et le `policyProfile`.

Maximum : 100 IDs uniques. Chaque ID doit exister dans le catalogue Checkov 3.3.8,
appartenir à un framework sélectionné et être autorisé par le profil. Une liste
vide est la valeur par défaut.

### `maxFindings`

Limite le nombre de lignes Dataset conservées.

Important : le résumé `OUTPUT` garde aussi les totaux complets. Donc si
`maxFindings` tronque le Dataset, l'utilisateur voit quand même qu'il y avait
plus de findings au total.

Valeur par défaut : 500. Valeurs autorisées : entier de 1 à 500. Un booléen, une
chaîne comme `"10"`, zéro ou 501 sont refusés.

## 5. Comment lire la sortie

L'Actor écrit deux sorties :

1. le Dataset par défaut ;
2. le record `OUTPUT`.

### Dataset : une ligne par politique échouée retenue

| Champ | Signification exacte |
|---|---|
| `schemaVersion` | Version du contrat public, actuellement `2`. |
| `scanId` | Identifiant de ce scan, identique à celui de `OUTPUT`. |
| `findingType` | Constante `IAC_MISCONFIGURATION`. |
| `policyProfile` | Profil réellement appliqué : `security` ou `all_iac`. |
| `framework` | Framework Checkov ayant produit le finding. |
| `checkId` | Identifiant stable de politique, par exemple `CKV_AWS_20`. |
| `checkName` | Nom lisible de la politique dans le catalogue épinglé. |
| `resource` | Nom normalisé de la ressource affectée. |
| `filePath` | Chemin POSIX relatif dans le snapshot, jamais un chemin machine absolu. |
| `lineStart` | Première ligne concernée ou `null` si Checkov ne la fournit pas. |
| `lineEnd` | Dernière ligne concernée ou `null`. |
| `checkovCategories` | Liste ordonnée complète des catégories natives Checkov. |
| `primaryCategory` | Première catégorie native, comptée une seule fois dans les totaux. |
| `severity` | Toujours `UNRATED`; aucune sévérité exploitable n'est inventée. |
| `findingFingerprint` | SHA-256 stable du finding, sans `scanId` ni numéros de lignes. |
| `policyReference` | Lien vers la source Checkov 3.3.8 épinglée; pas une promesse de correction. |
| `result` | Toujours `FAILED` dans le Dataset, car les passes ne deviennent pas des lignes. |
| `scannerVersion` | Version exacte du scanner : `3.3.8`. |

Le fingerprint permet de reconnaître le même finding entre deux scans même si
son numéro de ligne bouge. Il ne dit pas que deux repos différents sont identiques.

### `OUTPUT` : le résumé du run

| Champ | Signification exacte |
|---|---|
| `schemaVersion` | Version du contrat, actuellement `2`. |
| `scanId` | Identifiant partagé avec toutes les lignes Dataset. |
| `status` | État technique et fonctionnel décrit dans le tableau suivant. |
| `policyProfile` | Profil réellement appliqué. |
| `gateDecision` | Décision de gate : `PASS`, `FAIL` ou `UNKNOWN`. |
| `scanner` | Constante `Checkov`. |
| `scannerVersion` | Version épinglée `3.3.8`. |
| `frameworks` | Liste des frameworks réellement sélectionnés. |
| `durationMs` | Durée bornée du sous-processus Checkov en millisecondes. Ce n'est pas la durée totale du run. |
| `source` | Statistiques bornées de la source, détaillées ci-dessous. |
| `passedCount` | Nombre de politiques déclarées passées par Checkov. |
| `failedCount` | Nombre de politiques déclarées échouées. |
| `skippedCount` | Nombre de politiques déclarées ignorées. |
| `findingCount` | Nombre de lignes Dataset retenues après `maxFindings`. |
| `totalFindingCount` | Nombre complet de findings normalisés avant troncature. |
| `findingsByCategory` | Totaux complets par `primaryCategory`; leur somme égale `totalFindingCount`. |
| `truncated` | `true` si toutes les lignes n'ont pas été conservées. |
| `truncationReasons` | Raisons stables, actuellement `maxFindings` lorsque la limite agit. |
| `warnings` | Avertissements sûrs et bornés produits par la normalisation. |
| `error` | Erreur publique sûre, présente seulement lorsque `status = FAILED`. |

### Objet `source` dans `OUTPUT`

| Champ | Signification exacte |
|---|---|
| `kind` | `github`, `zip_upload`, ou `unknown` si l'échec est survenu très tôt. |
| `compressedBytes` | Nombre borné d'octets de l'archive acquise. |
| `fileCount` | Nombre borné de fichiers réguliers extraits. |
| `uncompressedBytes` | Total borné des octets extraits. |

Ces nombres servent à comprendre la taille du run. Ce ne sont ni du revenu, ni
une consommation facturée, ni un inventaire des ressources cloud.

### Objet `error` dans `OUTPUT`

| Champ | Signification exacte |
|---|---|
| `code` | Code technique public stable, par exemple `SCAN_TIMEOUT`. |
| `message` | Message court et sûr pour l'utilisateur. |
| `hint` | Conseil correctif optionnel. |

Les détails internes, tokens, contenus source, stack traces et payloads Checkov
bruts ne sont pas copiés dans cette erreur.

### Relation entre `status` et `gateDecision`

| `status` | `gateDecision` | Interprétation |
|---|---|---|
| `COMPLETED` | `PASS` | Checkov a terminé et aucun finding n'a été normalisé. |
| `COMPLETED_WITH_FINDINGS` | `FAIL` | Checkov a terminé et au moins une politique a échoué. Le run est livré avec succès. |
| `FAILED` | `UNKNOWN` | Erreur technique : il est interdit de conclure que l'IaC est sûre ou dangereuse. |

`FAIL` n'est donc pas un crash. `FAILED` est le crash technique. C'est la
distinction la plus importante pour comprendre l'Actor.

## 6. Test ZIP

Le ZIP de smoke test est :

```text
tests/fixtures/upload/iac-public-s3-smoke.zip
```

SHA-256 attendu :

```text
a76ff04581fa24a8f8843500c38f22f6e64cd1a1e433d373b87ef17092199756
```

Il contient volontairement un fichier Terraform vulnérable :

```text
tests/fixtures/vulnerable/main.tf
```

Ce fichier définit un bucket S3 public. Il est fait pour déclencher
`CKV_AWS_20`. Il ne doit jamais être déployé.

Input Console attendu :

```json
{
  "sourceType": "zip_upload",
  "frameworks": ["terraform"],
  "policyProfile": "security",
  "checkIds": ["CKV_AWS_20"],
  "maxFindings": 500
}
```

Résultat attendu :

- `status = COMPLETED_WITH_FINDINGS`
- `gateDecision = FAIL`
- `failedCount = 1`
- `findingCount = 1`
- `primaryCategory = GENERAL_SECURITY`
- `checkId = CKV_AWS_20`

Le test automatisé épinglé vérifie aussi 0 passe, 1 échec, le fingerprint
`1affa58e43cf0f2e522ca5512be90f664891cf6be68020bcf9bca988860b9f4b`,
le contenu exact du ZIP, son extraction sûre et sa reproductibilité binaire.
Ce résultat a été prouvé localement avec le vrai Checkov; il ne prétend pas être
un run cloud Apify.

## 7. Test GitHub

Input public reproductible :

```text
examples/input-public-github.json
```

Ce test utilise un repo public HashiCorp Education à un commit précis.

Résultat local observé :

- `status = COMPLETED_WITH_FINDINGS`
- `gateDecision = FAIL`
- 3 politiques passées ;
- 5 politiques échouées ;
- 5 lignes Dataset ;
- catégories : `ENCRYPTION=1`, `GENERAL_SECURITY=2`, `IAM=1`, `LOGGING=1`.

Ce test prouve le flux local GitHub + Checkov + Dataset + `OUTPUT`. Il ne prouve
pas encore la facturation cloud réelle.

## 8. Tests PASS, validation et erreur technique

### Test PASS

Pour isoler le contrat PASS avec le même ZIP, sélectionne uniquement
`checkIds = ["CKV_AWS_19"]`. Ce contrôle vérifie que le bucket n'autorise pas les
requêtes HTTP non chiffrées; le fixture ne contient aucune configuration qui
enfreint ce contrôle. Le résultat local exact est :

- `status = COMPLETED` ;
- `gateDecision = PASS` ;
- `passedCount = 1` et `failedCount = 0` ;
- `findingCount = 0` et Dataset vide ;
- absence de champ `error`.

Le même fichier reste vulnérable à `CKV_AWS_20`. Un PASS sur une seule règle ne
certifie donc ni le fichier complet, ni toute l'infrastructure.

### Test de validation

Pour vérifier le fail-closed sans lancer Checkov, envoie volontairement des
familles de sources mélangées :

```json
{
  "sourceType": "zip_upload",
  "repositoryUrl": "https://github.com/example/example",
  "archiveFile": "https://api.apify.com/v2/key-value-stores/STORE/records/source.zip",
  "frameworks": ["terraform"]
}
```

Résultat attendu : code `INPUT_SOURCE_EXCLUSIVE`, `status = FAILED` si le record
de failure a pu être écrit, et `gateDecision = UNKNOWN`. Aucun scan réussi ni
finding ne doit être déduit de cette erreur.

### Test d'erreur technique

Un timeout, un ZIP invalide ou une indisponibilité source doit produire `FAILED`
et `UNKNOWN`, jamais `PASS`. Le README contient la table complète des codes et
l'action utilisateur associée.

## 9. Troncature

La troncature arrive quand il y a plus de findings que `maxFindings`.

Exemple : si Checkov trouve 800 findings et que `maxFindings = 500`, le Dataset
contient 500 lignes, mais `OUTPUT.totalFindingCount` reste 800 et
`OUTPUT.truncated` devient `true`.

C'est important pour ne pas mentir à l'utilisateur : il voit que le résultat
Dataset est volontairement limité. Test concret avec le GitHub public : garde le
même commit, fixe `maxFindings` à 1, puis vérifie localement `findingCount = 1`,
`totalFindingCount = 5`, `truncated = true` et
`truncationReasons = ["maxFindings"]`. Ces totaux sont une preuve locale connue,
pas une promesse de résultat cloud futur si le code ou le snapshot change.

## 10. Sécurité, rétention et limites opérationnelles

- ZIP compressé : 20 MiB maximum; 500 fichiers réguliers; 100 MiB décompressés;
  50 MiB par fichier; ratio d'expansion 100:1.
- Checkov : timeout dur de 60 secondes, stdout 32 MiB et stderr 1 MiB.
- Archives chiffrées, liens, devices, chemins absolus ou traversants, archives
  imbriquées et compressions non supportées sont rejetés.
- Le workspace est privé et nettoyé logiquement. Ce n'est pas un effacement
  physique sécurisé du disque sous-jacent.
- Les lignes Dataset et `OUTPUT` restent dans les stockages Apify selon leur
  rétention. Le ZIP KVS uploadé appartient à l'appelant et n'est pas supprimé par
  cet Actor.
- L'Actor limite les chemins réseau connus de Checkov, mais n'offre pas une
  isolation egress au niveau kernel.
- Helm et Kustomize dépendent des binaires épinglés dans l'image.
- Les dépendances transitives `aiohttp` et `ecdsa` sont des limitations surveillées et non bloquantes tant qu'une ligne corrigée compatible n'est pas disponible.

## 11. Configuration de facturation live

Configuration live vérifiée le 2026-07-24 :

- modèle : Pay per event ;
- événements configurés : `apify-actor-start` et `completed-scan` ;
- prix standard Free de `completed-scan` : 0,50 $ ;
- remises Store actives : Bronze 0,45 $, Silver 0,40 $, Gold 0,35 $,
  Platinum 0,30 $ et Diamond 0,25 $ ;
- `apify-default-dataset-item` n'est pas configuré, donc le nombre de findings ne
  change pas le prix d'événement ;
- `apify-actor-start` conserve le prix officiel par défaut de 0,00005 $ par
  tranche de 1 Go, soit un total configuré de 0,00020 $ à 4 Go ;
- ce micro-événement suit la recommandation Apify et conserve la couverture du
  coût compute des cinq premières secondes ;
- `minimalMaxTotalChargeUsd = 0.51` est configuré et
  `maxTotalChargeUsd = 0.51` borne les runs.

Ce contrôle confirme la configuration live; il ne revendique aucun montant facturé observé pendant un run.

Apify résout le niveau d'abonnement du client en un prix effectif pour le run cloud.
Le code facture seulement le nom d'événement `completed-scan`; il n'essaie pas de
choisir lui-même le niveau ou le prix. Le simulateur local du SDK Python 4.0.0 ne
prouve pas cette résolution cloud. Un smoke cloud après activation du pricing reste
donc obligatoire. Le code transforme un `charged_count = 0` en `BILLING_FAILED`.
Comme les résultats ont déjà été persistés avant la facturation, il ne faut pas
relancer aveuglément après `BILLING_FAILED`.

## 12. Contrôles à chaque release

Checklist propriétaire :

1. Relire la configuration live sans la modifier.
2. Vérifier les six prix de `completed-scan` (Free 0,50 $, Bronze 0,45 $,
   Silver 0,40 $, Gold 0,35 $, Platinum 0,30 $, Diamond 0,25 $),
   `apify-actor-start` reste à 0,00005 $/Go,
   `apify-default-dataset-item` est absent, et
   `minimalMaxTotalChargeUsd = 0.51`.
3. Garder « Pay per event + usage » désactivé pour inclure l'usage plateforme
   dans le prix annoncé.
4. Garder `maxTotalChargeUsd = 0.51` sur les exemples et runs bornés.
5. Vérifier que les smokes cloud livrent Dataset et `OUTPUT`, sans transformer ce
   contrôle fonctionnel en affirmation de montant facturé observé.
6. Vérifier les scénarios PASS, FAIL, validation, timeout et troncature.
7. Aligner mot pour mot README, guide et snapshot pricing avec la configuration
   réellement lue.
