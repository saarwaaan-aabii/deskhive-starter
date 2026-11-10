# M5 Lab 1 — Notes de débrief (modèles, `Booking.clean()`, vérifications)

Ce document rassemble tout ce qu'il faut pour le débrief : le schéma des relations, les explications
(héritage abstrait, PROTECT, intervalles), le code de `Booking.clean()` expliqué ligne par ligne, et
les **résultats réels** de chaque vérification.

> Seul le corps de `Booking.clean()` dans `deskhive-web/bookings/models.py` a été modifié pour le lab.
> Ce fichier de notes n'est **pas** une modification de code.

## Sommaire

1. [Schéma des relations](#1-schéma-des-relations)
2. [Les clés primaires](#2-les-clés-primaires)
3. [Les contraintes de Space](#3-les-contraintes-de-space)
4. [Les ForeignKey et PROTECT](#4-les-foreignkey-et-protect)
5. [Héritage abstrait : `TimestampedModel`](#5-héritage-abstrait--timestampedmodel)
6. [`booking.pk` vs `booking.space_id` vs `booking.space`](#6-bookingpk-vs-bookingspace_id-vs-bookingspace)
7. [Migrations et catalogue](#7-migrations-et-catalogue)
8. [Les intervalles semi-ouverts et les prédictions](#8-les-intervalles-semi-ouverts-et-les-prédictions)
9. [`Booking.clean()` expliqué](#9-bookingclean-expliqué)
10. [Vérifications (résultats réels)](#10-vérifications-résultats-réels)
11. [Ce qui est prouvé… et ce qui ne l'est pas](#11-ce-qui-est-prouvé-et-ce-qui-ne-lest-pas)
12. [Exploration facultative : une migration de champ](#12-exploration-facultative--une-migration-de-champ)
13. [Checklist de débrief](#13-checklist-de-débrief)

---

## 1. Schéma des relations

```
┌──────────────────────────┐
│ Location                 │
│ PK: code  (texte, max 3) │   ex. "lyo", "lil", "bcn"
│ city, address            │
└────────────┬─────────────┘
             │ 1
             │  location = ForeignKey(Location, PROTECT, related_name='spaces')
             │ N
┌────────────▼─────────────┐
│ Space                    │
│ PK: id    (entier auto)  │
│ code  (unique)           │   ex. "lyo-desk"
│ capacity >= 1            │
│ hourly_rate > 0          │
└────────────┬─────────────┘
             │ 1
             │  space = ForeignKey(Space, PROTECT, related_name='bookings')
             │ N
┌────────────▼─────────────┐        N  ┌──────────────────────────┐
│ Booking                  │◄──────────│ Member                   │
│ PK: id    (entier auto)  │         1 │ PK: id    (entier auto)  │
│ start, end               │           │ email (unique)           │
│ end > start              │           │ full_name                │
└──────────────────────────┘           └──────────────────────────┘
   member = ForeignKey(Member, PROTECT, related_name='bookings')
```

| Relation | Cardinalité | Lecture |
|---|---|---|
| Location → Space | **1 à N** | une ville a plusieurs espaces ; un espace est dans une seule ville |
| Space → Booking | **1 à N** | un espace a plusieurs réservations ; une réservation concerne un seul espace |
| Member → Booking | **1 à N** | un membre a plusieurs réservations ; une réservation appartient à un seul membre |

Tous les modèles héritent de `TimestampedModel` (champ `created_at`).

> **📌 Résumé 1** — Location 1→N Space, Space 1→N Booking, Member 1→N Booking.
> La `ForeignKey` est toujours du côté « N » (dans `Space` et dans `Booking`).

---

## 2. Les clés primaires

Une **clé primaire** (*primary key*, `pk`) est la valeur qui identifie **une ligne de manière unique**
dans une table.

| Modèle | Clé primaire | Type | Exemple |
|---|---|---|---|
| `Location` | `code` (**explicite**, `primary_key=True`) | texte, `max_length=3` | `"lyo"` |
| `Space` | `id` (**automatique**) | entier (`BigAutoField`) | `1`, `2`… |
| `Member` | `id` (automatique) | entier | `1`, `2`… |
| `Booking` | `id` (automatique) | entier | `1`, `2`… |

Quand on n'écrit pas de `primary_key=True`, Django ajoute **tout seul** un champ `id` entier qui
s'incrémente (1, 2, 3…). On le voit dans la migration : `('id', models.BigAutoField(auto_created=True, primary_key=True, ...))`.

**Identifiant humain ≠ clé primaire.** `Space.code` (`"lyo-desk"`) et `Member.email` sont des
identifiants **lisibles par un humain**, marqués `unique=True` : deux espaces ne peuvent pas avoir le
même code, deux membres ne peuvent pas avoir le même email. Mais la clé primaire reste l'`id` entier,
qui est **stable** : si on corrige un email ou renomme un code, l'`id` ne change pas, et les
réservations qui pointent dessus restent valides.

> **📌 Résumé 2** — `Location` : clé texte explicite (3 caractères max). `Space`, `Member`,
> `Booking` : `id` entier automatique. `Space.code` et `Member.email` sont `unique`, mais restent
> séparés de la clé primaire.

---

## 3. Les contraintes de Space

```python
capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
hourly_rate = models.DecimalField(max_digits=7, decimal_places=2,
                                  validators=[MinValueValidator(Decimal('0.01'))])
class Meta:
    constraints = [
        models.CheckConstraint(condition=models.Q(capacity__gte=1), name='space_capacity_positive'),
        models.CheckConstraint(condition=models.Q(hourly_rate__gt=0), name='space_rate_positive'),
    ]
```

**`hourly_rate` : `max_digits=7, decimal_places=2`** → 7 chiffres **au total**, dont 2 après la
virgule. Donc au maximum `99999.99`. `DecimalField` évite les erreurs d'arrondi des nombres à virgule
flottante (important pour de l'argent).

| Contrainte | Condition | Sens |
|---|---|---|
| `space_capacity_positive` | `capacity__gte=1` | capacité **≥ 1** (`gte` = *greater than or equal*) |
| `space_rate_positive` | `hourly_rate__gt=0` | tarif **strictement > 0** (`gt` = *greater than*) |

Il y a **deux niveaux** de protection :
- les `validators` sont vérifiés par Django lors de `full_clean()` (formulaires) ;
- les `CheckConstraint` sont vérifiés par **la base de données** elle-même, même si quelqu'un
  contourne Django.

> **📌 Résumé 3** — Capacité ≥ 1, tarif > 0 (strictement). Tarif : 7 chiffres dont 2 décimales.
> Vérifié à la fois par Django (validators) et par la base (CheckConstraint).

---

## 4. Les ForeignKey et PROTECT

| ForeignKey | Dans | Cible | `related_name` | `on_delete` |
|---|---|---|---|---|
| `location` | `Space` | `Location` | `spaces` | `PROTECT` |
| `space` | `Booking` | `Space` | `bookings` | `PROTECT` |
| `member` | `Booking` | `Member` | `bookings` | `PROTECT` |

**`related_name`** = le nom pour remonter la relation **dans l'autre sens** :

```python
location.spaces.all()   # tous les espaces d'une ville
space.bookings.all()    # toutes les réservations d'un espace
member.bookings.all()   # toutes les réservations d'un membre
```

**`PROTECT`** = « **interdit** de supprimer un objet tant que d'autres en dépendent ». Résultat réel
(dans une transaction annulée ensuite) avec une réservation sur `lil-room` :

```
delete Location -> ProtectedError (PROTECT)
delete Space    -> ProtectedError (PROTECT)
delete Member   -> ProtectedError (PROTECT)
```

Sans `PROTECT` (par exemple avec `CASCADE`), supprimer une ville supprimerait en chaîne ses espaces
**et** toutes leurs réservations, sans prévenir.

> **📌 Résumé 4** — Chaque `ForeignKey` a une cible, un `related_name` (pour le sens inverse) et
> `PROTECT` : on ne peut pas supprimer une ville, un espace ou un membre encore utilisé.

---

## 5. Héritage abstrait : `TimestampedModel`

```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract = True
```

- `abstract = True` → ce modèle **ne crée pas de table** en base. C'est un **modèle « patron »**.
- Les modèles qui en héritent (`class Location(TimestampedModel)`) **reçoivent le champ `created_at`**
  dans **leur propre table**.
- `auto_now_add=True` → la date est remplie **automatiquement** à la création.

Vérifié : `TimestampedModel._meta.abstract` → `True`, et une réservation créée a bien un `created_at`.
Dans les migrations, chaque `CreateModel` contient `created_at` et indique `'abstract': False`
(les tables réelles ne sont pas abstraites).

> **📌 Résumé 5** — `TimestampedModel` partage `created_at` avec tous les modèles, **sans table à
> lui** (`abstract = True`). On écrit le champ une fois, on le réutilise partout.

---

## 6. `booking.pk` vs `booking.space_id` vs `booking.space`

Résultat réel pour une réservation sur `lil-room` :

```
booking.pk       = 1                                → la clé primaire de LA RÉSERVATION
booking.space_id = 4                                → l'id de l'espace, STOCKÉ dans la table booking
booking.space    = <Space: Lille Meeting Room>      → l'OBJET Space complet (code: lil-room)
```

| Écriture | Type | Requête en base ? |
|---|---|---|
| `booking.pk` | entier | non (déjà connu) |
| `booking.space_id` | entier | **non** : c'est la colonne stockée dans `bookings_booking` |
| `booking.space` | objet `Space` | **oui** la première fois : Django va chercher l'espace n°4 |

C'est pour ça que `clean()` utilise `space_id=self.space_id` dans le filtre : pas besoin de charger
l'objet `Space` pour comparer un numéro.

> **📌 Résumé 6** — `pk` = numéro de la réservation. `space_id` = numéro de l'espace, stocké.
> `space` = l'objet Space, chargé via ce numéro.

---

## 7. Migrations et catalogue

| Fichier | Ce qu'il établit |
|---|---|
| `spaces/migrations/0001_initial.py` | crée les tables `Location` (pk `code`, max 3) et `Space` (pk `id` auto, `code` unique, FK `location` PROTECT, 2 `CheckConstraint`) |
| `spaces/migrations/0002_seed_catalogue.py` | **migration de données** (`RunPython`) : insère 3 villes et 6 espaces |
| `bookings/migrations/0001_initial.py` | crée `Member` (`email` unique) et `Booking` (FK `space` et `member` PROTECT, contrainte `end > start`). Dépend de `spaces.0001_initial` |

- **Migration appliquée** `[X]` = elle a déjà modifié la base.
- **Migration en attente** `[ ]` = le fichier existe dans le code, mais la base n'a pas encore changé.

Catalogue réel après `migrate` :

```
3 locations : lyo (Lyon), lil (Lille), bcn (Barcelona)
6 spaces    : lyo-desk, lyo-room, lil-desk, lil-room, bcn-desk, bcn-room
```

> **📌 Résumé 7** — 2 migrations de schéma + 1 migration de données. 3 villes, 6 espaces.
> `[X]` = appliquée, `[ ]` = en attente. Ne jamais supprimer la base ni régénérer ces migrations.

---

## 8. Les intervalles semi-ouverts et les prédictions

DeskHive utilise des **intervalles semi-ouverts** `[start, end)` : le début est inclus, la fin
**exclue**. Une réservation 10:00–11:00 occupe 10:00 jusqu'à **juste avant** 11:00.

**Règle de conflit** : une réservation existante gêne une nouvelle si

```
existant.start < nouveau.end   ET   existant.end > nouveau.start
```

Les comparaisons sont **strictes** (`<`, `>`). Donc si `existant.end == nouveau.start` (11:00 = 11:00),
`11:00 > 11:00` est **faux** → **pas de conflit** : les réservations **adjacentes** sont permises.

```
Existant :        [10:00 ─────── 11:00)
10:30–11:30 :            [10:30 ─────── 11:30)      ✗ chevauche
09:00–12:00 :  [09:00 ───────────────────────── 12:00)   ✗ contient l'existant
11:00–12:00 :                    [11:00 ─────── 12:00)   ✓ adjacent
```

**Prédictions vérifiées** — réservation existante : `lyo-desk`, 15/01/2030, 10:00–11:00
(créée dans une transaction **annulée** ensuite : 0 réservation en base après) :

| Candidat | Prévu | Résultat réel de `clean()` |
|---|---|---|
| Même espace, 10:30–11:30 | Conflit | ❌ `This space is already booked for part of that interval.` |
| Même espace, 09:00–12:00 | Conflit (contient l'existant) | ❌ `This space is already booked for part of that interval.` |
| Même espace, 11:00–12:00 | Adjacent, valide | ✅ VALID |
| Autre espace (`lyo-room`), 10:00–11:00 | Pas de conflit | ✅ VALID |
| Début = fin | Durée invalide | ❌ `Duration must be positive and at most 12 hours` |
| Fin avant début | Durée invalide | ❌ `Duration must be positive and at most 12 hours` |
| Exactement 12 h, sans conflit | Autorisé | ✅ VALID |
| Plus de 12 h | Durée invalide | ❌ `Duration must be positive and at most 12 hours` |
| Re-valider la réservation existante | Ne doit pas entrer en conflit avec elle-même | ✅ VALID |

**Question du quiz** — *Which booking is valid under DeskHive's conflict rules?*
→ **A booking that ends exactly when the next one begins** (adjacence).

> **📌 Résumé 8** — Intervalles `[start, end)`. Conflit si `start_existant < end_nouveau` ET
> `end_existant > start_nouveau`. Comparaisons strictes → l'adjacence est permise ; contenir une
> réservation est un conflit. Les 9 prédictions sont confirmées.

---

## 9. `Booking.clean()` expliqué

```python
def clean(self):
    super().clean()                                                      # ①
    if self.start is None or self.end is None:                           # ②
        return
    local_start, local_end = local_interval(self.start, self.end)        # ③
    try:
        validate_booking(local_start, local_end)                         # ④
    except (InvalidBookingError, ValueError) as exc:
        raise ValidationError(str(exc)) from exc                         # ⑤
    if self.space_id is None:                                            # ⑥
        return
    conflicts = Booking.objects.filter(                                  # ⑦
        space_id=self.space_id, start__lt=self.end, end__gt=self.start)
    if self.pk is not None:                                              # ⑧
        conflicts = conflicts.exclude(pk=self.pk)
    if conflicts.exists():                                               # ⑨
        raise ValidationError('This space is already booked for part of that interval.')
```

| # | Ligne | Pourquoi |
|---|---|---|
| ① | `super().clean()` | garde la validation normale de Django (méthode de la classe parente) |
| ② | `start` ou `end` absent → `return` | on ne valide pas un intervalle **incomplet** ; Django signalera le champ manquant ailleurs |
| ③ | `local_interval(...)` | convertit les dates « aware » (avec fuseau) en heures **locales de Paris, sans fuseau** (« naive »), comme l'attend `deskhive-core`. Si l'intervalle traverse un changement d'heure, l'adaptateur lève **lui-même** une `ValidationError` Django : on la laisse passer **telle quelle** (pas de `try` autour) |
| ④ | `validate_booking(...)` | règle métier : durée **> 0** et **≤ 12 h** |
| ⑤ | `raise ValidationError(str(exc)) from exc` | traduit l'erreur Python en erreur **Django**, en gardant **le message** (`str(exc)`) et **la cause** (`from exc`, utile pour déboguer) |
| ⑥ | pas d'espace → `return` | impossible de chercher des conflits sans savoir quel espace |
| ⑦ | `Booking.objects.filter(...)` | les réservations **du même espace** qui chevauchent. On utilise les dates **d'origine** (`self.start`, `self.end`, avec fuseau), pas les versions locales. `__lt` = `<`, `__gt` = `>` (stricts → adjacence permise) |
| ⑧ | `.exclude(pk=self.pk)` | si la réservation existe déjà (modification), on **la retire** des candidats : sinon elle serait en conflit **avec elle-même** |
| ⑨ | `.exists()` | demande juste « y en a-t-il au moins une ? » (plus rapide que tout charger). Si oui → erreur contenant **« already booked »** |

**Ce que `clean()` ne fait pas** : pas de `save()` (valider ≠ enregistrer), pas de `return` de
dictionnaire. Elle signale les problèmes **uniquement par des exceptions**.

> **📌 Résumé 9** — `clean()` : validation Django → intervalle complet ? → durée valide (dates
> locales) → conflit dans le même espace (dates d'origine), **sans compter la réservation elle-même**
> → erreur « already booked ». Aucune sauvegarde.

---

## 10. Vérifications (résultats réels)

Environnement : Python 3.12.3, `.venv` à la racine, `deskhive-core` installé en mode éditable.

**Migrations** — `manage.py showmigrations spaces bookings` (après `migrate`) :
```
spaces
 [X] 0001_initial
 [X] 0002_seed_catalogue
bookings
 [X] 0001_initial
```

**Schéma inchangé** — `manage.py makemigrations --check --dry-run` :
```
No changes detected
```

**Tests d'échafaudage :**
```
test_seed_and_keys_and_abstract_inheritance ... ok   (Ran 1 test — OK)
test_space_constraints ...                      ok   (Ran 1 test — OK)
```

**Durées isolées dans le shell** (objet `Booking` **non enregistré**, `lyo-desk`, Europe/Paris,
membre volontairement omis) :

| Cas | `error.messages` |
|---|---|
| début = fin | `['Duration must be positive and at most 12 hours']` |
| fin avant début | `['Duration must be positive and at most 12 hours']` |
| durée > 12 h | `['Duration must be positive and at most 12 hours']` |

Nombre de réservations en base avant / après : `0 → 0` (rien n'a été enregistré).
Le message parle bien de **durée**, et non plus du TODO temporaire `Complete M5 lab 1`.

> **📌 Résumé 10** — Migrations appliquées, schéma inchangé, 2 tests d'échafaudage OK, 3 erreurs de
> durée claires, aucune réservation enregistrée.

---

## 11. Ce qui est prouvé… et ce qui ne l'est pas

**Réflexion — que prouve la vérification de durée dans le shell ?**

Elle **prouve** que :
- `clean()` n'utilise plus le rejet temporaire du TODO ;
- les dates « aware » passent bien par `local_interval`, puis par `validate_booking` ;
- une `InvalidBookingError` est bien **traduite** en `ValidationError` Django avec un **message utile** ;
- tout cela **sans rien enregistrer**.

Elle **ne prouve pas** :
- **la détection de chevauchement** : il faudrait au moins une réservation **déjà enregistrée** dans
  le même espace (ici, il n'y en a aucune) ;
- **l'auto-exclusion** : il faudrait une réservation **avec une clé primaire** qu'on re-valide pendant
  une modification ;
- la **validation complète** du modèle (`full_clean()`), puisque le membre est volontairement omis.

**Tests reportés au lab CRUD.** Les tests `test_overlap_rejected_but_adjacent_allowed` et
`test_booking_update_excludes_itself` créent leurs réservations via `save_booking()`, qui est encore
un TODO du lab 2 (`ValidationError: Complete M5 lab 2: save_booking().`). Ils ne peuvent donc pas
encore confirmer ce lab tout seuls. Résultat actuel de `bookings.test_m5` : 14 tests, 5 OK, 9 en
échec — **tous** à cause du travail des labs suivants (`save_booking`, vues CRUD, AJAX). Une suite M5
100 % verte n'est **pas** l'objectif de ce lab. (Les scénarios de chevauchement et d'auto-exclusion
ont toutefois été vérifiés manuellement à la section 8, dans une transaction annulée.)

**Les 3 points à retenir pour le débrief :**

1. **Adjacence** : une réservation qui se termine exactement quand une autre commence ne crée **pas**
   de chevauchement (comparaisons strictes, intervalles semi-ouverts).
2. **Auto-exclusion** : une réservation existante ne doit pas entrer en conflit **avec elle-même**
   quand on la modifie → `exclude(pk=self.pk)`.
3. **M4 ne persiste rien** : la confirmation de demande en M4 est stockée en **session**, pas en base.
   Elle ne crée **aucun** enregistrement et ne peut donc pas déclencher la vérification de conflit
   du modèle.

> **📌 Résumé 11** — Le test de durée prouve la traduction des erreurs de durée ; il ne prouve ni le
> chevauchement, ni l'auto-exclusion, qui demandent des réservations enregistrées (lab CRUD).

---

## 12. Exploration facultative : une migration de champ

Faite sur une branche **jetable** (`tmp-explore-description`), puis **supprimée**.

1. Ajout dans `Space` : `description = models.TextField(default='')`
2. `makemigrations spaces` a généré `spaces/migrations/0003_space_description.py` :

```python
class Migration(migrations.Migration):
    dependencies = [
        ("spaces", "0002_seed_catalogue"),       # ← dépend de la dernière migration
    ]
    operations = [
        migrations.AddField(
            model_name="space",                  # ← le modèle
            name="description",                  # ← le champ
            field=models.TextField(default=""),  # ← le type et la valeur par défaut
        ),
    ]
```

3. `showmigrations` affichait `[ ] 0003_space_description` → **en attente**, jamais appliquée.
   La migration n'a **pas** été lancée sur la base de travail.
4. Nettoyage : suppression du fichier généré (nom vérifié avec `git status`, pas deviné), retour du
   modèle à l'état d'origine, suppression de la branche. Ensuite : `makemigrations --check --dry-run`
   → `No changes detected`.

**Pourquoi un `default` ?** Les 6 espaces existent déjà : il faut une valeur pour remplir la nouvelle
colonne sur ces lignes.

**Attention** : supprimer un fichier de migration ne fait que supprimer du **code Python**. Si la
migration avait déjà été appliquée, la base garderait la colonne.

> **📌 Résumé 12** — Une migration enregistre le modèle, le champ, le défaut et sa dépendance.
> Supprimer le fichier n'annule pas une migration déjà appliquée.

---

## 13. Checklist de débrief

- [x] Le schéma des relations montre les clés et cardinalités de Location, Space, Member et Booking (§1, §2)
- [x] Explication de l'héritage abstrait et de PROTECT (§4, §5)
- [x] `Booking.clean()` complété uniquement dans le fichier du modèle existant (§9)
- [x] Vérification du schéma inchangé et résultats des deux tests d'échafaudage disponibles (§10)
- [x] Les vérifications isolées de durée invalide lèvent des erreurs de validation claires (§10)
- [x] Explication de l'adjacence, de l'auto-exclusion et des tests reportés au lab CRUD (§8, §11)
