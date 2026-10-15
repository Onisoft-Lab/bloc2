---
title: VéloVille — soutenance
lang: fr
theme: default
colorSchema: light
highlighter: shiki
lineNumbers: false
drawings:
  enabled: false
transition: none
fonts:
  sans: Atkinson Hyperlegible
  serif: Bricolage Grotesque
  mono: IBM Plex Mono
  provider: google
background: "#e4ecef"
layout: none
---

<div class="totem">
  <div class="borne">
    <p>Épreuve E.2 · bloc 2</p>
    <h1>VéloVille</h1>
    <p>Hauts-de-France</p>
  </div>
  <div class="plan">
    <h2>Plan</h2>
    <div class="filet"></div>
    <ol>
      <li><span class="duree">1</span> Contexte et périmètre</li>
      <li><span class="duree">2</span> Démonstration</li>
      <li><span class="duree">3</span> Choix techniques et qualité</li>
      <li><span class="duree">4</span> Limites</li>
    </ol>
  </div>
</div>

---

# Contexte et périmètre

**Besoin.** VéloVille a des exports billettique sales. Il faut les fiabiliser, les exposer en API, et les restituer à l'exploitant et à la direction.

**Architecture.** CSV → règles pures → PostgreSQL → FastAPI → Streamlit. Le front n'ouvre pas la base. Postgres en Docker, port 5432. UV pour le venv, `requirements.txt` reste installable en pip.

**Livré.** Import idempotent, API JWT (2 rôles), 4 écrans tabulaires, tests, recette, sauvegarde, docs.

**Pas livré.** Graphiques, météo, anticipation de charge, purge 13 mois.

---

# Démo · audit et import

Chaque ligne CSV a un seul sort : retenue, rejet ou doublon.

| Fichier | Retenues | Rejets | Doublons |
|---|---:|---:|---:|
| Stations | 120 | 0 | 0 |
| Trajets | 2&nbsp;002 | 16 | 12 |
| Incidents | 177 | 3 | 0 |

- Trajets : 9 durées ≤ 0, 7 arrivées `S999`. Arrivée vide conservée (RG3).
- `T480596` rejeté pour durée, sa copie = doublon.
- Incidents : 3 dates de résolution antérieures au signalement.
- Technicien absent = avertissement, ligne gardée.

Journal : `docs/journal-import.csv` (fichier, id, colonne, valeur, motif, décision).

Idempotence : `ON CONFLICT DO NOTHING`. Seconde exécution → toujours 120 / 2&nbsp;002 / 177.

---

# Démo · connexion et droits

Comptes : `exploitant01` et `direction01`. Jeton jamais affiché.

- Sans jeton → **401**
- Direction sur `PUT /incidents/.../statut` → **403** « Acces reserve au role exploitant »
- Exploitant `ouvert` → `en_cours` → **200**
- Même PUT une 2ᵉ fois → **422**

```python
def exiger_exploitant(...):
    if utilisateur["role"] != "exploitant":
        raise HTTPException(403, "Acces reserve au role exploitant")
```

Front direction : message, pas de formulaire. `usager_ref` nulle part à l'écran.

---

# Démo · quatre écrans

1. **Connexion** — identifiant + rôle en sidebar, déconnexion.
2. **Stations** — `S001` Lille - Gare ; Lille = 46 ; page hors borne → « Aucun résultat pour ces critères. »
3. **Incidents** — 177 lignes ; formulaire statut = exploitant seulement.
4. **Indicateurs** — 2&nbsp;002 trajets, 10 stations actives (`S094`), délai 129,4 h.

API coupée → « L'API est injoignable. Vérifiez qu'elle est démarrée. » Pas de trace Python.

---
layout: two-cols-header
---

# Démo · indicateur = SQL

`GET /indicateurs/activite-par-jour?date_debut=2026-08-24&date_fin=2026-08-30`

::left::

<table class="compact">
  <thead>
    <tr><th>Jour</th><th class="num">Trajets</th></tr>
  </thead>
  <tbody>
    <tr><td>24</td><td class="num">329</td></tr>
    <tr><td>25</td><td class="num">311</td></tr>
    <tr><td>26</td><td class="num">306</td></tr>
    <tr><td>27</td><td class="num">300</td></tr>
    <tr><td>28</td><td class="num">315</td></tr>
    <tr><td>29</td><td class="num">219</td></tr>
    <tr><td>30</td><td class="num">222</td></tr>
  </tbody>
</table>

::right::

```sql
SELECT depart_horodatage::date, count(*)
FROM trajet
WHERE depart_horodatage::date
  BETWEEN '2026-08-24' AND '2026-08-30'
GROUP BY 1 ORDER BY 1;
```

::bottom::

Somme = 2&nbsp;002 = `total` de `GET /trajets` sur la même période. Même résultat ligne à ligne ; le test unitaire refait cette comparaison.

---

# Démo · tests et sauvegarde

`make test` → **27 tests**, couverture `api/services` = **99 %** (seuil demandé : 60 %).

Le test qui change un statut remet la ligne d'origine.

`make sauvegarde` → `pg_dump -Fc` horodaté dans `sauvegardes/`.

- `pg_dump` sur le PATH si dispo, sinon `docker compose exec`
- échec ou fichier vide → exit non nul

---

# Choix techniques et qualité

**Structure.** Fiabilisation = fonctions pures. Routeurs = validation + délégation. Indicateurs = SQL.

**Sécurité.** JWT HS256, secret dans `.env`. bcrypt. Même message pour inconnu / mauvais MDP. PUT statut = exploitant.

**Éco.** Pagination serveur (max 100), pas d'auto-refresh, communes en cache 1 h, agrégats SQL.

**Git.** Branche `feature/front` fusionnée. Tags `v0.1.0`, `v0.2.0`, `v1.0.0`.

**Recette.** 13/10/2026 : REC-01 à REC-10, 10 OK, 0 anomalie, prononcée. Pas de correctif après.

---

# Limites

1. Pas de purge des trajets > 13 mois.
2. Pas d'IHM de gestion des comptes (`sql/comptes.sql` seulement).
3. `usager_ref` encore renvoyé par l'API au rôle direction.
4. Météo / anticipation de charge : hors V1.

---
layout: none
---

<div class="totem">
  <div class="borne">
    <p>Épreuve E.2 · bloc 2</p>
    <h1>Questions</h1>
    <p>API et base démarrées</p>
  </div>
  <div class="plan">
    <h2>À disposition</h2>
    <div class="filet"></div>
    <ol>
      <li>Une commande</li>
      <li>Un fichier</li>
      <li>Un extrait de code</li>
    </ol>
  </div>
</div>
