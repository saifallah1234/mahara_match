# Mahara Match — Frontend

Interface web de la plateforme d'intermédiation emploi, compétences et formation.
Projet académique, Faculté des Sciences de Bizerte, 2026–2027.

React 18 · TypeScript · Vite 6 · Tailwind CSS 4 · React Router 6

---

## Démarrer

```bash
npm install
npm run dev        # http://localhost:5173
```

Autres commandes : `npm run build` (compile et vérifie les types), `npm run preview`
(sert le build de production).

L'écran de connexion utilise l'API Django : e-mail et mot de passe, jeton d'accès
en mémoire, rafraîchissement par cookie HttpOnly et sélection d'espace après
authentification. En développement, Vite transmet `/api` au backend sur le port 8000.
Lancer Django avec `backend.config.settings.development` : cette configuration
autorise les origines CSRF `http://localhost:5173` et `http://127.0.0.1:5173`.
Cela fonctionne aussi depuis un navigateur Windows lorsque les serveurs tournent
dans WSL et que les ports locaux sont accessibles.
`npm test` vérifie les règles de redirection. Les données métier des tableaux de
bord restent une démonstration et sont signalées comme telles dans l'interface.

---

## Ce que couvre l'interface

Cinq espaces, un par acteur retenu.

| Espace | Pages |
|---|---|
| Chercheur d'emploi | tableau de bord, profil, CV, offres, candidatures, formations, assistant |
| Employeur / Recruteur | tableau de bord, entreprise et filiales, offres, pipeline, entretiens |
| Organisme de formation | tableau de bord, programmes, sessions et inscriptions |
| Responsable du ministère | indicateurs régionaux, compétences du marché |
| Administrateur | comptes et rôles, organisations, référentiels, imports, journal d'audit |

---

## Organisation du code

```
src/
  lib/
    types.ts          Types du domaine, calqués sur le modèle de données logique
    matching.ts       Calcul de couverture des compétences
    statusMachine.ts  Machine à états de la candidature
    format.ts         Libellés français et formatage
  data/
    referentials.ts   Compétences, niveaux, langues, matrice RBAC
    seed.ts           Jeu de données de démonstration
  api/
    client.ts         Transport HTTP, rafraîchissement et règles métier de démonstration
    auth.ts           Contrats d'identité et appels API
  state/
    auth.tsx          Session authentifiée et espace sélectionné
    store.tsx         Données métier de démonstration et identité réelle
  components/
    ui.tsx            Boutons, panneaux, champs, tableaux, modales
    domain.tsx        Registre de correspondance, frise de statuts, provenance CV
    charts.tsx        Graphiques du tableau de bord ministère
    layout.tsx        Coquille applicative et navigation par rôle
  pages/              Une page par route
```

---

## Les trois règles métier portées par le frontend

**1. Le score de correspondance se recalcule à la main** (`lib/matching.ts`)

Une compétence obligatoire pèse 2 points, une compétence souhaitée 1 point.
Le score est le rapport des points couverts sur les points demandés.

```
SQL      obligatoire  poids 2   couverte     2 / 2
Python   obligatoire  poids 2   couverte     2 / 2
Docker   souhaitée    poids 1   absente      0 / 1
                                             ─────
                                             4 / 5     100 × 4 / 5 = 80 %
```

Le registre affiche toujours ce calcul en clair. Une compétence déclarée mais
non confirmée par le candidat ne compte pas. Une offre sans compétence
renseignée affiche « score indisponible » au lieu d'un chiffre inventé.

Le score sert à classer et à expliquer, jamais à écarter automatiquement.
`rankOffers` départage deux offres de même score par le nombre de points
demandés, pour qu'une offre à une seule compétence souhaitée n'éclipse pas
une offre exigeante.

**2. Les transitions de candidature sont contrôlées** (`lib/statusMachine.ts`)

```
Soumise → En examen → Présélectionnée → Entretien → Proposée → Recrutée
   └──────────┴───────────────┴──────────────┴──────────┴──→ Refusée (recruteur)
   └──────────┴───────────────┴──────────────┴──────────┴──→ Retirée (candidat)
```

Chaque transition vérifie le statut courant et le rôle de l'auteur. Une
transition absente de la table est refusée. Le candidat ne peut retirer son
dossier qu'avant la décision finale ; le recruteur est seul à faire avancer
ou refuser. Chaque changement est historisé et visible des deux côtés.

**3. L'agent conversationnel n'agit qu'après confirmation** (`pages/candidat/Assistant.tsx`)

L'agent prépare, affiche un récapitulatif, et attend un accord explicite.
Au moment du clic, les droits et l'ouverture de l'offre sont revérifiés par
`checkApply` — la même fonction que l'espace candidat. Une donnée absente est
signalée, jamais estimée. L'agent n'est pas un acteur : c'est un composant
interne qui agit sous l'identité et les permissions de l'utilisateur.

---

## Données métier encore à brancher

L'authentification et les listes d'identité de l'administration viennent de
l'API réelle. Les autres données métier viennent encore de `src/data/seed.ts`.

1. Brancher chaque domaine sur ses services API avec `request(...)` :

```ts
export async function listOffers(): Promise<JobOffer[]> {
  return request<JobOffer[]>('/offers')
}
```

2. Dans `src/state/store.tsx`, remplacer les `useState(SEED)` par un chargement
   via ces fonctions.

Les types de domaine actuels sont conçus pour la démonstration et peuvent
nécessiter une adaptation aux contrats API réels.
`checkApply` et `checkTransition` restent utiles côté client pour désactiver
les actions impossibles, mais le backend doit refaire ces contrôles : ils ne
font pas autorité depuis le navigateur.

Les noms de champs sont en camelCase côté interface; adapter chaque réponse API
à la frontière du domaine concerné.

---

## Identité visuelle

Reprise de la présentation du projet.

| Jeton | Valeur | Usage |
|---|---|---|
| `navy` | `#10252F` | texte principal, rail de navigation |
| `teal` | `#0E7C86` | couleur de marque, actions |
| `cyan` | `#7FE0E6` | accents sur fond sombre |
| `coral` | `#E63946` | manques, refus |
| `leaf` | `#2E9E6B` | compétences couvertes, succès |
| `amber` | `#E9A23B` | lecture incertaine, en attente |
| `cream` | `#F7F5F0` | fond de page |

Typographie : IBM Plex Sans Arabic, choisie pour couvrir le latin et l'arabe —
l'assistant répond en français, en arabe et en tunisien. IBM Plex Mono est
réservée à l'expression du calcul de couverture.

Les couleurs des graphiques (`#0092A3` et `#C77D1A`) sont des pas plus saturés
de la même famille, validés sur la séparation en vision déficiente et le
contraste sur fond clair.

---

## Limites connues

- Les données sont fictives et en mémoire : un rechargement de page les remet
  à l'état initial.
- L'import de CV simule l'extraction ; PyMuPDF et Tesseract tournent côté
  backend.
- Les réponses de l'assistant sont construites à partir des données réelles du
  magasin, mais ne passent pas encore par un LLM.
- Le forum communautaire et la planification avancée des entretiens sont
  post-MVP et ne sont pas implémentés.
- Interface en français uniquement ; seul l'assistant accepte l'arabe et le
  tunisien. Le passage de toute l'interface en RTL reste à faire.
