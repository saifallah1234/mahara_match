import type { EducationLevel, Language, Permission, RoleCode, Skill } from '../lib/types'

/* Référentiel normalisé des compétences. Les alias évitent les doublons
   ambigus : « Postgres » et « PL/SQL » pointent vers la même compétence. */
export const SKILLS: Skill[] = [
  { id: 'sk-sql', canonicalName: 'SQL', category: 'TECHNIQUE', aliases: ['Postgres', 'PostgreSQL', 'PL/SQL', 'MySQL'], description: 'Interrogation et manipulation de bases relationnelles.' },
  { id: 'sk-python', canonicalName: 'Python', category: 'TECHNIQUE', aliases: ['Python 3', 'py'], description: 'Langage de programmation généraliste.' },
  { id: 'sk-docker', canonicalName: 'Docker', category: 'OUTIL', aliases: ['Conteneurisation', 'docker-compose'], description: 'Conteneurisation et exécution reproductible.' },
  { id: 'sk-js', canonicalName: 'JavaScript', category: 'TECHNIQUE', aliases: ['JS', 'ES6'] },
  { id: 'sk-react', canonicalName: 'React', category: 'TECHNIQUE', aliases: ['ReactJS', 'React.js'] },
  { id: 'sk-java', canonicalName: 'Java', category: 'TECHNIQUE', aliases: ['Java SE', 'JEE'] },
  { id: 'sk-spring', canonicalName: 'Spring Boot', category: 'TECHNIQUE', aliases: ['Spring'] },
  { id: 'sk-excel', canonicalName: 'Excel', category: 'OUTIL', aliases: ['Microsoft Excel', 'tableur'] },
  { id: 'sk-powerbi', canonicalName: 'Power BI', category: 'OUTIL', aliases: ['PowerBI'] },
  { id: 'sk-git', canonicalName: 'Git', category: 'OUTIL', aliases: ['GitHub', 'GitLab'] },
  { id: 'sk-ml', canonicalName: 'Machine learning', category: 'TECHNIQUE', aliases: ['apprentissage automatique', 'scikit-learn'] },
  { id: 'sk-compta', canonicalName: 'Comptabilité générale', category: 'METIER', aliases: ['compta'] },
  { id: 'sk-paie', canonicalName: 'Gestion de la paie', category: 'METIER', aliases: ['paie'] },
  { id: 'sk-vente', canonicalName: 'Techniques de vente', category: 'METIER', aliases: ['vente', 'commercial'] },
  { id: 'sk-soudure', canonicalName: 'Soudure', category: 'METIER', aliases: ['soudage', 'soudeur'] },
  { id: 'sk-elec', canonicalName: 'Électricité bâtiment', category: 'METIER', aliases: ['électricien', 'installation électrique'] },
  { id: 'sk-couture', canonicalName: 'Confection textile', category: 'METIER', aliases: ['couture', 'piquage'] },
  { id: 'sk-relation', canonicalName: 'Relation client', category: 'TRANSVERSALE', aliases: ['service client', 'accueil'] },
  { id: 'sk-equipe', canonicalName: 'Travail en équipe', category: 'TRANSVERSALE', aliases: ['collaboration'] },
  { id: 'sk-redaction', canonicalName: 'Rédaction professionnelle', category: 'TRANSVERSALE', aliases: ['rédaction'] },
]

export const EDUCATION_LEVELS: EducationLevel[] = [
  { id: 'ed-bac', name: 'Baccalauréat', levelOrder: 1 },
  { id: 'ed-bts', name: 'BTS / BTP', levelOrder: 2 },
  { id: 'ed-licence', name: 'Licence', levelOrder: 3 },
  { id: 'ed-master', name: 'Mastère', levelOrder: 4 },
  { id: 'ed-ing', name: 'Diplôme d’ingénieur', levelOrder: 5 },
  { id: 'ed-doc', name: 'Doctorat', levelOrder: 6 },
]

export const LANGUAGES: Language[] = [
  { id: 'lg-ar', code: 'ar', name: 'Arabe' },
  { id: 'lg-fr', code: 'fr', name: 'Français' },
  { id: 'lg-en', code: 'en', name: 'Anglais' },
  { id: 'lg-de', code: 'de', name: 'Allemand' },
  { id: 'lg-it', code: 'it', name: 'Italien' },
]

/* Matrice RBAC : les autorisations sont accordées par rôle. */
export const PERMISSIONS: Permission[] = [
  { code: 'profile.read.own', resource: 'Profil', action: 'Consulter le sien' },
  { code: 'profile.write.own', resource: 'Profil', action: 'Modifier le sien' },
  { code: 'offer.read', resource: 'Offre', action: 'Consulter' },
  { code: 'offer.write', resource: 'Offre', action: 'Créer et publier' },
  { code: 'application.create', resource: 'Candidature', action: 'Déposer' },
  { code: 'application.transition', resource: 'Candidature', action: 'Changer le statut' },
  { code: 'training.write', resource: 'Formation', action: 'Publier et gérer' },
  { code: 'stats.read', resource: 'Indicateurs', action: 'Consulter les agrégats' },
  { code: 'account.manage', resource: 'Comptes', action: 'Gérer comptes et rôles' },
  { code: 'referential.manage', resource: 'Référentiels', action: 'Gérer' },
  { code: 'audit.read', resource: 'Audit', action: 'Consulter les journaux' },
]

export const ROLE_PERMISSIONS: Record<RoleCode, string[]> = {
  CANDIDATE: ['profile.read.own', 'profile.write.own', 'offer.read', 'application.create'],
  RECRUITER: ['offer.read', 'offer.write', 'application.transition'],
  TRAINING_MANAGER: ['training.write', 'offer.read'],
  MINISTRY_MANAGER: ['stats.read'],
  ADMIN: ['account.manage', 'referential.manage', 'audit.read', 'offer.read', 'stats.read'],
}

export const skillName = (id: string) => SKILLS.find((s) => s.id === id)?.canonicalName ?? id
