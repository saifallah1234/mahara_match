import type {
  Application,
  AuditLog,
  CandidateProfile,
  CVAnalysisResult,
  CVDocument,
  DataSource,
  ExtractedField,
  ImportBatch,
  ImportRow,
  Interview,
  JobOffer,
  Notification,
  Organization,
  TrainingEnrollment,
  TrainingProgram,
  TrainingSession,
  User,
} from '../lib/types'

/* ------------------------------------------------------------------ */
/* Organisations                                                       */
/* ------------------------------------------------------------------ */

export const ORGANIZATIONS: Organization[] = [
  { id: 'org-telnet', type: 'COMPANY', legalName: 'Groupe TelNet', matriculeFiscal: '0914257TAM000', governorate: 'Tunis', city: 'Tunis', websiteUrl: 'https://telnet.tn', description: 'Ingénierie logicielle et systèmes embarqués.', verificationStatus: 'VERIFIED', createdAt: '2025-11-04T09:00:00Z' },
  { id: 'org-telnet-ariana', parentId: 'org-telnet', type: 'SUBSIDIARY', legalName: 'TelNet Ariana', matriculeFiscal: '0914258TAM001', governorate: 'Ariana', city: 'Ariana', verificationStatus: 'VERIFIED', createdAt: '2025-11-04T09:10:00Z' },
  { id: 'org-telnet-sfax', parentId: 'org-telnet', type: 'SUBSIDIARY', legalName: 'TelNet Sfax', matriculeFiscal: '0914259TAM002', governorate: 'Sfax', city: 'Sfax', verificationStatus: 'VERIFIED', createdAt: '2026-01-12T09:00:00Z' },
  { id: 'org-cofat', type: 'COMPANY', legalName: 'COFAT Bizerte', matriculeFiscal: '0441209BAM000', governorate: 'Bizerte', city: 'Menzel Jemil', description: 'Faisceaux électriques pour l’automobile.', verificationStatus: 'VERIFIED', createdAt: '2025-12-02T10:00:00Z' },
  { id: 'org-medis', type: 'COMPANY', legalName: 'Laboratoires Médis', matriculeFiscal: '0332118NAM000', governorate: 'Nabeul', city: 'Nabeul', description: 'Industrie pharmaceutique.', verificationStatus: 'VERIFIED', createdAt: '2026-02-18T08:30:00Z' },
  { id: 'org-sartex', type: 'COMPANY', legalName: 'Sartex Group', matriculeFiscal: '0556331MAM000', governorate: 'Monastir', city: 'Ksar Hellal', description: 'Confection et textile.', verificationStatus: 'PENDING', createdAt: '2026-09-21T14:20:00Z' },
  { id: 'org-codeline', type: 'TRAINING_PROVIDER', legalName: 'Code Line Academy', matriculeFiscal: '1182447TAM000', governorate: 'Tunis', city: 'Lac 2', description: 'Formations courtes en développement et données.', verificationStatus: 'VERIFIED', createdAt: '2025-10-15T11:00:00Z' },
  { id: 'org-iset', type: 'TRAINING_PROVIDER', legalName: 'ISET Bizerte — Formation continue', matriculeFiscal: '0771556BAM000', governorate: 'Bizerte', city: 'Bizerte', verificationStatus: 'VERIFIED', createdAt: '2025-10-20T11:00:00Z' },
  { id: 'org-ministere', type: 'MINISTRY', legalName: 'Ministère de l’Emploi et de la Formation professionnelle', governorate: 'Tunis', city: 'Tunis', verificationStatus: 'VERIFIED', createdAt: '2025-09-01T08:00:00Z' },
]

/* ------------------------------------------------------------------ */
/* Utilisateurs — un par rôle, plus des candidats pour les listes      */
/* ------------------------------------------------------------------ */

export const USERS: User[] = [
  { id: 'u-emna', email: 'emna.khelifi@example.tn', firstName: 'Emna', lastName: 'Khelifi', phone: '+216 20 114 882', status: 'ACTIVE', roles: ['CANDIDATE'], emailVerifiedAt: '2026-08-02T10:12:00Z', lastLoginAt: '2026-09-30T18:40:00Z' },
  { id: 'u-yassine', email: 'yassine.gharbi@example.tn', firstName: 'Yassine', lastName: 'Gharbi', status: 'ACTIVE', roles: ['CANDIDATE'], lastLoginAt: '2026-09-28T09:05:00Z' },
  { id: 'u-nour', email: 'nour.belhaj@example.tn', firstName: 'Nour', lastName: 'Belhaj', status: 'ACTIVE', roles: ['CANDIDATE'], lastLoginAt: '2026-09-29T17:22:00Z' },
  { id: 'u-mehdi', email: 'mehdi.trabelsi@example.tn', firstName: 'Mehdi', lastName: 'Trabelsi', status: 'ACTIVE', roles: ['CANDIDATE'], lastLoginAt: '2026-09-25T12:00:00Z' },
  { id: 'u-sarra', email: 'sarra.jlassi@example.tn', firstName: 'Sarra', lastName: 'Jlassi', status: 'ACTIVE', roles: ['CANDIDATE'], lastLoginAt: '2026-09-30T08:44:00Z' },
  { id: 'u-hamza', email: 'hamza.ouali@example.tn', firstName: 'Hamza', lastName: 'Ouali', status: 'PENDING', roles: ['CANDIDATE'] },
  { id: 'u-sofiane', email: 'sofiane.mabrouk@telnet.tn', firstName: 'Sofiane', lastName: 'Mabrouk', status: 'ACTIVE', roles: ['RECRUITER'], organizationId: 'org-telnet-ariana', jobTitle: 'Responsable recrutement', lastLoginAt: '2026-09-30T16:10:00Z' },
  { id: 'u-leila', email: 'leila.ferchichi@codeline.tn', firstName: 'Leila', lastName: 'Ferchichi', status: 'ACTIVE', roles: ['TRAINING_MANAGER'], organizationId: 'org-codeline', jobTitle: 'Responsable pédagogique', lastLoginAt: '2026-09-29T14:00:00Z' },
  { id: 'u-nadia', email: 'nadia.bouzid@emploi.gov.tn', firstName: 'Nadia', lastName: 'Bouzid', status: 'ACTIVE', roles: ['MINISTRY_MANAGER'], organizationId: 'org-ministere', jobTitle: 'Chargée des statistiques', lastLoginAt: '2026-09-30T09:00:00Z' },
  { id: 'u-admin', email: 'admin@mahara-match.tn', firstName: 'Rania', lastName: 'Saidi', status: 'ACTIVE', roles: ['ADMIN'], jobTitle: 'Administratrice plateforme', lastLoginAt: '2026-09-30T19:02:00Z' },
]

/* ------------------------------------------------------------------ */
/* Profils candidats                                                   */
/* ------------------------------------------------------------------ */

export const CANDIDATE_PROFILES: CandidateProfile[] = [
  {
    id: 'cp-emna',
    userId: 'u-emna',
    birthDate: '2003-04-18',
    governorate: 'Bizerte',
    city: 'Bizerte',
    headline: 'Jeune diplômée en informatique de gestion',
    summary:
      'Licence en informatique de gestion. Stage de fin d’études sur un tableau de bord de suivi de production. À l’aise avec les bases de données et l’analyse de données.',
    employmentStatus: 'En recherche active',
    desiredJobTitle: 'Développeuse junior',
    availabilityDate: '2026-10-15',
    profileVisibility: 'RECRUITERS',
    completionScore: 82,
    maxDistanceKm: 50,
    relocation: 'OPEN_TO_RELOCATE',
    preferredWorkMode: 'HYBRID',
    experiences: [
      { id: 'xp-1', organizationName: 'COFAT Bizerte', jobTitle: 'Stagiaire — informatique de gestion', startDate: '2026-02-01', endDate: '2026-06-30', description: 'Tableau de bord de suivi de production sous Excel et requêtes SQL sur la base de production.' },
      { id: 'xp-2', organizationName: 'Association Jeunes Bizerte', jobTitle: 'Bénévole — soutien numérique', startDate: '2025-09-01', endDate: '2026-01-15', description: 'Ateliers d’initiation à la bureautique pour demandeurs d’emploi.' },
    ],
    educations: [
      { id: 'ed-1', institution: 'Faculté des Sciences de Bizerte', fieldOfStudy: 'Informatique de gestion', educationLevelId: 'ed-licence', startYear: 2023, endYear: 2026 },
      { id: 'ed-2', institution: 'Lycée Ibn Khaldoun, Bizerte', fieldOfStudy: 'Sciences expérimentales', educationLevelId: 'ed-bac', startYear: 2019, endYear: 2023 },
    ],
    certifications: [
      { id: 'cert-1', name: 'Databases and SQL for Data Science', certificationOrganization: 'Coursera — IBM', issueDate: '2026-05-20', credentialId: 'XQ8R2-44D1' },
    ],
    projects: [
      { id: 'pj-1', name: 'Suivi de production COFAT', role: 'Développeuse', description: 'Tableau de bord de production alimenté par des requêtes SQL et restitué dans Excel.', startDate: '2026-02-01', endDate: '2026-06-30', technologies: ['SQL', 'Excel', 'Python'] },
      { id: 'pj-2', name: 'Gestion de bibliothèque universitaire', role: 'Développeuse', description: 'Projet académique : application de gestion des emprunts.', startDate: '2025-10-01', endDate: '2026-01-20', technologies: ['Python', 'SQL'], repositoryUrl: 'https://github.com/exemple/biblio' },
    ],
    skills: [
      { skillId: 'sk-sql', level: 'AVANCE', yearsExperience: 2, validated: true, source: 'CV' },
      { skillId: 'sk-python', level: 'INTERMEDIAIRE', yearsExperience: 2, validated: true, source: 'CV' },
      { skillId: 'sk-excel', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'CV' },
      { skillId: 'sk-git', level: 'INTERMEDIAIRE', yearsExperience: 1, validated: true, source: 'SAISIE' },
      { skillId: 'sk-equipe', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'SAISIE' },
      { skillId: 'sk-js', level: 'DEBUTANT', yearsExperience: 1, validated: false, source: 'CV' },
    ],
    languages: [
      { languageId: 'lg-ar', level: 'NATIF' },
      { languageId: 'lg-fr', level: 'C1' },
      { languageId: 'lg-en', level: 'B2' },
    ],
  },
  {
    id: 'cp-yassine',
    userId: 'u-yassine',
    governorate: 'Ariana',
    city: 'Ariana',
    headline: 'Développeur full-stack — 3 ans d’expérience',
    employmentStatus: 'En poste, à l’écoute',
    desiredJobTitle: 'Développeur full-stack',
    profileVisibility: 'RECRUITERS',
    completionScore: 94,
    maxDistanceKm: 20,
    relocation: 'CANNOT_RELOCATE',
    preferredWorkMode: 'HYBRID',
    experiences: [{ id: 'xp-y1', organizationName: 'Vermeg', jobTitle: 'Développeur full-stack', startDate: '2023-09-01', description: 'Applications métier en React et Spring Boot.' }],
    educations: [{ id: 'ed-y1', institution: 'INSAT', fieldOfStudy: 'Génie logiciel', educationLevelId: 'ed-ing', startYear: 2018, endYear: 2023 }],
    certifications: [],
    projects: [],
    skills: [
      { skillId: 'sk-sql', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'CV' },
      { skillId: 'sk-python', level: 'INTERMEDIAIRE', yearsExperience: 2, validated: true, source: 'CV' },
      { skillId: 'sk-docker', level: 'INTERMEDIAIRE', yearsExperience: 2, validated: true, source: 'CV' },
      { skillId: 'sk-js', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'CV' },
      { skillId: 'sk-react', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'CV' },
      { skillId: 'sk-git', level: 'EXPERT', yearsExperience: 4, validated: true, source: 'CV' },
    ],
    languages: [{ languageId: 'lg-ar', level: 'NATIF' }, { languageId: 'lg-fr', level: 'C1' }, { languageId: 'lg-en', level: 'C1' }],
  },
  {
    id: 'cp-nour',
    userId: 'u-nour',
    governorate: 'Bizerte',
    city: 'Menzel Bourguiba',
    headline: 'Technicienne en confection textile',
    summary: 'Dix ans d’atelier, sans diplôme formel. Compétences acquises sur le terrain.',
    employmentStatus: 'En recherche active',
    desiredJobTitle: 'Chef de ligne confection',
    profileVisibility: 'RECRUITERS',
    completionScore: 61,
    maxDistanceKm: 50,
    relocation: 'CANNOT_RELOCATE',
    preferredWorkMode: 'ONSITE',
    experiences: [{ id: 'xp-n1', organizationName: 'Atelier de confection, Menzel Bourguiba', jobTitle: 'Piqueuse puis chef d’équipe', startDate: '2016-03-01', endDate: '2026-07-31', description: 'Encadrement d’une ligne de 12 personnes.' }],
    educations: [{ id: 'ed-n1', institution: 'Centre de formation professionnelle de Bizerte', fieldOfStudy: 'Confection', educationLevelId: 'ed-bac', startYear: 2014, endYear: 2016 }],
    certifications: [],
    projects: [],
    skills: [
      { skillId: 'sk-couture', level: 'EXPERT', yearsExperience: 10, validated: true, source: 'SAISIE' },
      { skillId: 'sk-equipe', level: 'AVANCE', yearsExperience: 6, validated: true, source: 'SAISIE' },
      { skillId: 'sk-relation', level: 'INTERMEDIAIRE', yearsExperience: 4, validated: false, source: 'SAISIE' },
    ],
    languages: [{ languageId: 'lg-ar', level: 'NATIF' }, { languageId: 'lg-fr', level: 'B1' }],
  },
  {
    id: 'cp-mehdi',
    userId: 'u-mehdi',
    governorate: 'Sfax',
    city: 'Sfax',
    headline: 'Data analyst junior',
    employmentStatus: 'En recherche active',
    desiredJobTitle: 'Data analyst',
    profileVisibility: 'PUBLIC',
    completionScore: 77,
    maxDistanceKm: 100,
    relocation: 'OPEN_TO_RELOCATE',
    preferredWorkMode: 'REMOTE',
    experiences: [{ id: 'xp-m1', organizationName: 'Cabinet conseil Sfax', jobTitle: 'Analyste de données', startDate: '2025-01-05', endDate: '2026-08-31' }],
    educations: [{ id: 'ed-m1', institution: 'FSEG Sfax', fieldOfStudy: 'Business intelligence', educationLevelId: 'ed-master', startYear: 2021, endYear: 2025 }],
    certifications: [],
    projects: [],
    skills: [
      { skillId: 'sk-sql', level: 'AVANCE', yearsExperience: 3, validated: true, source: 'CV' },
      { skillId: 'sk-powerbi', level: 'AVANCE', yearsExperience: 2, validated: true, source: 'CV' },
      { skillId: 'sk-excel', level: 'EXPERT', yearsExperience: 5, validated: true, source: 'CV' },
      { skillId: 'sk-python', level: 'INTERMEDIAIRE', yearsExperience: 1, validated: true, source: 'CV' },
    ],
    languages: [{ languageId: 'lg-ar', level: 'NATIF' }, { languageId: 'lg-fr', level: 'C1' }, { languageId: 'lg-en', level: 'B2' }],
  },
  {
    id: 'cp-sarra',
    userId: 'u-sarra',
    governorate: 'Ariana',
    city: 'Raoued',
    headline: 'Gestionnaire de paie',
    employmentStatus: 'En recherche active',
    desiredJobTitle: 'Gestionnaire de paie',
    profileVisibility: 'RECRUITERS',
    completionScore: 88,
    maxDistanceKm: 20,
    relocation: 'CANNOT_RELOCATE',
    preferredWorkMode: 'ONSITE',
    experiences: [{ id: 'xp-s1', organizationName: 'Cabinet comptable Tunis', jobTitle: 'Assistante paie', startDate: '2022-06-01', endDate: '2026-09-01' }],
    educations: [{ id: 'ed-s1', institution: 'ISG Tunis', fieldOfStudy: 'Comptabilité', educationLevelId: 'ed-licence', startYear: 2019, endYear: 2022 }],
    certifications: [],
    projects: [],
    skills: [
      { skillId: 'sk-paie', level: 'AVANCE', yearsExperience: 4, validated: true, source: 'CV' },
      { skillId: 'sk-compta', level: 'AVANCE', yearsExperience: 4, validated: true, source: 'CV' },
      { skillId: 'sk-excel', level: 'AVANCE', yearsExperience: 4, validated: true, source: 'CV' },
    ],
    languages: [{ languageId: 'lg-ar', level: 'NATIF' }, { languageId: 'lg-fr', level: 'C1' }],
  },
  {
    id: 'cp-hamza',
    userId: 'u-hamza',
    governorate: 'Bizerte',
    city: 'Ras Jebel',
    headline: 'Soudeur qualifié',
    employmentStatus: 'En recherche active',
    desiredJobTitle: 'Soudeur',
    profileVisibility: 'PRIVATE',
    completionScore: 34,
    maxDistanceKm: 50,
    relocation: 'OPEN_TO_RELOCATE',
    preferredWorkMode: 'ONSITE',
    experiences: [],
    educations: [],
    certifications: [],
    projects: [],
    skills: [{ skillId: 'sk-soudure', level: 'AVANCE', yearsExperience: 7, validated: false, source: 'SAISIE' }],
    languages: [{ languageId: 'lg-ar', level: 'NATIF' }],
  },
]

/* ------------------------------------------------------------------ */
/* CV et extraction                                                    */
/* ------------------------------------------------------------------ */

export const CVS: CVDocument[] = [
  { id: 'cv-emna-3', candidateId: 'cp-emna', title: 'CV — Développeuse junior (v3)', languageCode: 'fr', isPrimary: true, parseStatus: 'PARSED', versionNumber: 3, fileName: 'CV_Emna_Khelifi_2026.pdf', sizeBytes: 284_112, uploadedAt: '2026-09-12T10:04:00Z', ocrUsed: false, pageCount: 2 },
  { id: 'cv-emna-2', candidateId: 'cp-emna', title: 'CV — version scannée', languageCode: 'fr', isPrimary: false, parseStatus: 'PARSED', versionNumber: 2, fileName: 'CV_scan_aout.jpg', sizeBytes: 1_842_330, uploadedAt: '2026-08-03T15:40:00Z', ocrUsed: true, pageCount: 1 },
  { id: 'cv-emna-1', candidateId: 'cp-emna', title: 'CV — première version', languageCode: 'fr', isPrimary: false, parseStatus: 'PARSED', versionNumber: 1, fileName: 'cv_emna.pdf', sizeBytes: 198_220, uploadedAt: '2026-08-02T11:20:00Z', ocrUsed: false, pageCount: 1 },
  { id: 'cv-yassine-1', candidateId: 'cp-yassine', title: 'CV 2026', languageCode: 'fr', isPrimary: true, parseStatus: 'PARSED', versionNumber: 1, fileName: 'yassine_gharbi.pdf', sizeBytes: 311_900, uploadedAt: '2026-06-18T09:00:00Z', ocrUsed: false, pageCount: 2 },
  { id: 'cv-mehdi-1', candidateId: 'cp-mehdi', title: 'CV data analyst', languageCode: 'fr', isPrimary: true, parseStatus: 'PARSED', versionNumber: 1, fileName: 'mehdi_cv.pdf', sizeBytes: 265_400, uploadedAt: '2026-09-02T13:15:00Z', ocrUsed: false, pageCount: 1 },
  { id: 'cv-sarra-1', candidateId: 'cp-sarra', title: 'CV paie', languageCode: 'fr', isPrimary: true, parseStatus: 'PARSED', versionNumber: 1, fileName: 'sarra_jlassi.pdf', sizeBytes: 240_100, uploadedAt: '2026-09-10T08:00:00Z', ocrUsed: false, pageCount: 1 },
]

/** Champs proposés par l'extraction du CV scanné, avec leur provenance.
    La date de stage a été mal reconnue par l'OCR : c'est la correction type. */
export const EXTRACTED_FIELDS: ExtractedField[] = [
  { id: 'ef-1', label: 'Nom et prénom', value: 'Emna Khelifi', sourcePage: 1, sourceExcerpt: 'EMNA KHELIFI — Bizerte', confidence: 0.98, status: 'PROPOSED' },
  { id: 'ef-2', label: 'Téléphone', value: '+216 20 114 882', sourcePage: 1, sourceExcerpt: 'Tél : 20 114 882', confidence: 0.94, status: 'PROPOSED' },
  { id: 'ef-3', label: 'Diplôme', value: 'Licence en informatique de gestion — Faculté des Sciences de Bizerte', sourcePage: 1, sourceExcerpt: 'Licence informatique de gestion, FSB, 2023-2026', confidence: 0.91, status: 'PROPOSED' },
  { id: 'ef-4', label: 'Stage — début', value: '2026-02-01', sourcePage: 1, sourceExcerpt: 'Stage PFE : Fév. 2026 – Juin 2026, COFAT', confidence: 0.88, status: 'PROPOSED' },
  { id: 'ef-5', label: 'Stage — fin', value: '2020-06-30', sourcePage: 1, sourceExcerpt: 'Stage PFE : Fév. 2026 – Juin 2026, COFAT', confidence: 0.41, status: 'PROPOSED' },
  { id: 'ef-6', label: 'Employeur du stage', value: 'COFAT Bizerte', sourcePage: 1, sourceExcerpt: 'COFAT Bizerte — service informatique', confidence: 0.95, status: 'PROPOSED' },
  { id: 'ef-7', label: 'Compétence', value: 'SQL', sourcePage: 1, sourceExcerpt: 'Compétences : SQL, Excel, Python', confidence: 0.96, status: 'PROPOSED' },
  { id: 'ef-8', label: 'Compétence', value: 'Excel', sourcePage: 1, sourceExcerpt: 'Compétences : SQL, Excel, Python', confidence: 0.96, status: 'PROPOSED' },
  { id: 'ef-9', label: 'Compétence', value: 'Python', sourcePage: 1, sourceExcerpt: 'Compétences : SQL, Excel, Python', confidence: 0.93, status: 'PROPOSED' },
  { id: 'ef-10', label: 'Langue', value: 'Français — C1', sourcePage: 1, sourceExcerpt: 'Français : courant', confidence: 0.79, status: 'PROPOSED' },
]

export const CV_ANALYSES: CVAnalysisResult[] = [
  {
    id: 'an-1',
    cvId: 'cv-emna-3',
    overallScore: 78,
    analyzedAt: '2026-09-12T10:06:00Z',
    checks: [
      { code: 'TEXT_EXTRACTABLE', label: 'Texte extractible sans OCR', passed: true, detail: 'Les deux pages contiennent une couche de texte.' },
      { code: 'SECTIONS', label: 'Rubriques attendues présentes', passed: true, detail: 'Expérience, formation, compétences et contact sont identifiés.' },
      { code: 'CONTACT', label: 'Coordonnées lisibles', passed: true, detail: 'Téléphone et adresse e-mail détectés en page 1.' },
      { code: 'NO_TABLE_LAYOUT', label: 'Mise en page sans tableau complexe', passed: false, detail: 'La rubrique compétences est dans un tableau à deux colonnes : certains ATS la lisent mal.' },
      { code: 'NO_IMAGE_TEXT', label: 'Aucun texte en image', passed: true, detail: 'Aucune zone de texte sous forme d’image.' },
      { code: 'DATES_FORMAT', label: 'Dates au format cohérent', passed: false, detail: 'Deux formats coexistent : « Fév. 2026 » et « 02/2026 ».' },
    ],
    suggestions: [
      'Remplacer le tableau des compétences par une liste simple.',
      'Uniformiser le format des dates sur l’ensemble du document.',
      'Ajouter une ligne d’accroche sous le nom pour annoncer le poste visé.',
    ],
  },
]

/* ------------------------------------------------------------------ */
/* Offres                                                              */
/* ------------------------------------------------------------------ */

export const JOB_OFFERS: JobOffer[] = [
  {
    id: 'of-218',
    reference: 'OF-218',
    organizationId: 'org-telnet-ariana',
    createdBy: 'u-sofiane',
    title: 'Développeur junior',
    description:
      'Au sein de l’équipe plateforme, vous participez au développement de services de traitement de données : écriture de requêtes, scripts d’alimentation et contrôles de qualité. Poste ouvert aux profils débutants ayant une première expérience de stage.',
    contractType: 'CDI',
    workMode: 'HYBRID',
    governorate: 'Ariana',
    city: 'Ariana',
    experienceLevel: 'DEBUTANT',
    minSalary: 1200,
    maxSalary: 1600,
    applicationDeadline: '2026-10-31',
    status: 'PUBLISHED',
    publishedAt: '2026-09-15T09:00:00Z',
    easyApply: true,
    educationLevelId: 'ed-licence',
    requiredLanguageId: 'lg-fr',
    skills: [
      { skillId: 'sk-sql', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-python', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-docker', importance: 'SOUHAITEE', requiredLevel: 'DEBUTANT' },
    ],
  },
  {
    id: 'of-224',
    reference: 'OF-224',
    organizationId: 'org-telnet-ariana',
    createdBy: 'u-sofiane',
    title: 'Développeur full-stack React / Spring',
    description: 'Développement d’applications métier pour des clients du secteur bancaire.',
    contractType: 'CDI',
    workMode: 'HYBRID',
    governorate: 'Ariana',
    city: 'Ariana',
    experienceLevel: 'CONFIRME',
    minSalary: 2200,
    maxSalary: 3000,
    applicationDeadline: '2026-11-15',
    status: 'PUBLISHED',
    publishedAt: '2026-09-20T10:30:00Z',
    easyApply: true,
    educationLevelId: 'ed-ing',
    skills: [
      { skillId: 'sk-js', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-react', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-java', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-spring', importance: 'SOUHAITEE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-docker', importance: 'SOUHAITEE', requiredLevel: 'DEBUTANT' },
    ],
  },
  {
    id: 'of-231',
    reference: 'OF-231',
    organizationId: 'org-cofat',
    createdBy: 'u-sofiane',
    title: 'Analyste données de production',
    description: 'Suivi des indicateurs de production, construction de tableaux de bord et automatisation des rapports hebdomadaires.',
    contractType: 'CDD',
    workMode: 'ONSITE',
    governorate: 'Bizerte',
    city: 'Menzel Jemil',
    experienceLevel: 'JUNIOR',
    applicationDeadline: '2026-10-20',
    status: 'PUBLISHED',
    publishedAt: '2026-09-18T08:00:00Z',
    easyApply: true,
    educationLevelId: 'ed-licence',
    skills: [
      { skillId: 'sk-excel', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-sql', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-powerbi', importance: 'SOUHAITEE', requiredLevel: 'INTERMEDIAIRE' },
    ],
  },
  {
    id: 'of-240',
    reference: 'OF-240',
    organizationId: 'org-medis',
    createdBy: 'u-sofiane',
    title: 'Gestionnaire de paie',
    description: 'Établissement des bulletins, déclarations sociales et suivi des dossiers du personnel.',
    contractType: 'CDI',
    workMode: 'ONSITE',
    governorate: 'Nabeul',
    city: 'Nabeul',
    experienceLevel: 'CONFIRME',
    minSalary: 1800,
    applicationDeadline: '2026-10-25',
    status: 'PUBLISHED',
    publishedAt: '2026-09-22T11:00:00Z',
    easyApply: true,
    skills: [
      { skillId: 'sk-paie', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-compta', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-excel', importance: 'SOUHAITEE', requiredLevel: 'INTERMEDIAIRE' },
    ],
  },
  {
    id: 'of-245',
    reference: 'OF-245',
    organizationId: 'org-sartex',
    createdBy: 'u-sofiane',
    title: 'Chef de ligne confection',
    description: 'Encadrement d’une ligne de production, contrôle qualité et suivi des cadences.',
    contractType: 'CDI',
    workMode: 'ONSITE',
    governorate: 'Monastir',
    city: 'Ksar Hellal',
    experienceLevel: 'CONFIRME',
    status: 'PUBLISHED',
    publishedAt: '2026-09-24T07:30:00Z',
    easyApply: true,
    skills: [
      { skillId: 'sk-couture', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-equipe', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
    ],
  },
  {
    id: 'of-248',
    reference: 'OF-248',
    organizationId: 'org-telnet-sfax',
    createdBy: 'u-sofiane',
    title: 'Ingénieur données — plateforme',
    description: 'Conception et exploitation de pipelines d’ingestion, qualité des données et supervision.',
    contractType: 'CDI',
    workMode: 'REMOTE',
    governorate: 'Sfax',
    city: 'Sfax',
    experienceLevel: 'CONFIRME',
    minSalary: 2400,
    maxSalary: 3200,
    applicationDeadline: '2026-11-30',
    status: 'PUBLISHED',
    publishedAt: '2026-09-26T09:15:00Z',
    easyApply: true,
    skills: [
      { skillId: 'sk-python', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-sql', importance: 'OBLIGATOIRE', requiredLevel: 'AVANCE' },
      { skillId: 'sk-docker', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' },
      { skillId: 'sk-git', importance: 'SOUHAITEE', requiredLevel: 'INTERMEDIAIRE' },
    ],
  },
  {
    id: 'of-252',
    reference: 'OF-252',
    organizationId: 'org-cofat',
    createdBy: 'u-sofiane',
    title: 'Électricien de maintenance',
    description: 'Maintenance préventive et corrective des installations électriques de l’atelier.',
    contractType: 'CDI',
    workMode: 'ONSITE',
    governorate: 'Bizerte',
    city: 'Menzel Jemil',
    experienceLevel: 'JUNIOR',
    status: 'PUBLISHED',
    publishedAt: '2026-09-28T08:00:00Z',
    easyApply: false,
    externalUrl: 'https://cofat.example.tn/carrieres/OF-252',
    skills: [{ skillId: 'sk-elec', importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' }],
  },
  {
    id: 'of-199',
    reference: 'OF-199',
    organizationId: 'org-telnet-ariana',
    createdBy: 'u-sofiane',
    title: 'Testeur QA junior',
    description: 'Rédaction et exécution de plans de test fonctionnels.',
    contractType: 'SIVP',
    workMode: 'ONSITE',
    governorate: 'Ariana',
    city: 'Ariana',
    experienceLevel: 'DEBUTANT',
    status: 'CLOSED',
    publishedAt: '2026-07-01T09:00:00Z',
    closedAt: '2026-09-10T17:00:00Z',
    easyApply: true,
    skills: [{ skillId: 'sk-git', importance: 'SOUHAITEE', requiredLevel: 'DEBUTANT' }],
  },
  {
    id: 'of-255',
    reference: 'OF-255',
    organizationId: 'org-telnet-ariana',
    createdBy: 'u-sofiane',
    title: 'Chargé de relation client',
    description: 'Accueil, qualification des demandes et suivi des dossiers clients.',
    contractType: 'CDD',
    workMode: 'ONSITE',
    governorate: 'Tunis',
    city: 'Tunis',
    experienceLevel: 'DEBUTANT',
    status: 'DRAFT',
    easyApply: true,
    skills: [],
  },
  {
    id: 'of-260',
    reference: 'OF-260',
    organizationId: 'org-medis',
    createdBy: 'u-sofiane',
    title: 'Opérateur de production — importée',
    description: 'Offre collectée auprès d’une source partenaire autorisée.',
    contractType: 'CDD',
    workMode: 'ONSITE',
    governorate: 'Nabeul',
    city: 'Grombalia',
    experienceLevel: 'DEBUTANT',
    status: 'PUBLISHED',
    publishedAt: '2026-09-29T06:00:00Z',
    easyApply: false,
    externalUrl: 'https://api.aneti.tn/offres/ANETI-1001',
    sourceId: 'src-aneti',
    externalId: 'ANETI-1001',
    skills: [{ skillId: 'sk-equipe', importance: 'SOUHAITEE', requiredLevel: 'DEBUTANT' }],
  },
]

/* ------------------------------------------------------------------ */
/* Candidatures                                                        */
/* ------------------------------------------------------------------ */

export const APPLICATIONS: Application[] = [
  {
    id: 'ap-1',
    candidateId: 'cp-emna',
    offerId: 'of-231',
    cvId: 'cv-emna-3',
    status: 'PRESELECTED',
    coverLetter: 'Mon stage de fin d’études portait précisément sur le suivi de production chez COFAT. Je connais déjà la base de production et les indicateurs suivis.',
    appliedAt: '2026-09-19T09:22:00Z',
    history: [
      { id: 'h-1', status: 'SUBMITTED', changedAt: '2026-09-19T09:22:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-2', status: 'UNDER_REVIEW', changedAt: '2026-09-21T14:05:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-3', status: 'PRESELECTED', reason: 'Expérience directe sur le même environnement de production.', changedAt: '2026-09-24T10:40:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-2',
    candidateId: 'cp-emna',
    offerId: 'of-218',
    cvId: 'cv-emna-3',
    status: 'UNDER_REVIEW',
    coverLetter: 'Je couvre SQL et Python, les deux compétences obligatoires de l’offre. Docker n’apparaît pas encore dans mon profil : je suis inscrite à une formation qui démarre le mois prochain.',
    appliedAt: '2026-09-26T16:10:00Z',
    history: [
      { id: 'h-4', status: 'SUBMITTED', changedAt: '2026-09-26T16:10:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-5', status: 'UNDER_REVIEW', changedAt: '2026-09-29T09:15:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-3',
    candidateId: 'cp-emna',
    offerId: 'of-199',
    cvId: 'cv-emna-1',
    status: 'REJECTED',
    appliedAt: '2026-08-05T11:00:00Z',
    history: [
      { id: 'h-6', status: 'SUBMITTED', changedAt: '2026-08-05T11:00:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-7', status: 'UNDER_REVIEW', changedAt: '2026-08-12T10:00:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-8', status: 'REJECTED', reason: 'Poste pourvu par un profil déjà formé à l’outil interne.', changedAt: '2026-08-28T15:30:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-4',
    candidateId: 'cp-yassine',
    offerId: 'of-224',
    cvId: 'cv-yassine-1',
    status: 'INTERVIEW',
    coverLetter: 'Trois ans sur une stack React et Spring Boot comparable.',
    appliedAt: '2026-09-21T08:30:00Z',
    history: [
      { id: 'h-9', status: 'SUBMITTED', changedAt: '2026-09-21T08:30:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-10', status: 'UNDER_REVIEW', changedAt: '2026-09-22T09:00:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-11', status: 'PRESELECTED', changedAt: '2026-09-23T11:20:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-12', status: 'INTERVIEW', reason: 'Entretien technique planifié.', changedAt: '2026-09-25T16:00:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-5',
    candidateId: 'cp-yassine',
    offerId: 'of-218',
    cvId: 'cv-yassine-1',
    status: 'SUBMITTED',
    appliedAt: '2026-09-29T19:45:00Z',
    history: [{ id: 'h-13', status: 'SUBMITTED', changedAt: '2026-09-29T19:45:00Z', changedByRole: 'CANDIDATE' }],
  },
  {
    id: 'ap-6',
    candidateId: 'cp-mehdi',
    offerId: 'of-231',
    cvId: 'cv-mehdi-1',
    status: 'SUBMITTED',
    appliedAt: '2026-09-28T13:00:00Z',
    history: [{ id: 'h-14', status: 'SUBMITTED', changedAt: '2026-09-28T13:00:00Z', changedByRole: 'CANDIDATE' }],
  },
  {
    id: 'ap-7',
    candidateId: 'cp-mehdi',
    offerId: 'of-248',
    cvId: 'cv-mehdi-1',
    status: 'UNDER_REVIEW',
    appliedAt: '2026-09-27T10:12:00Z',
    history: [
      { id: 'h-15', status: 'SUBMITTED', changedAt: '2026-09-27T10:12:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-16', status: 'UNDER_REVIEW', changedAt: '2026-09-30T08:20:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-8',
    candidateId: 'cp-sarra',
    offerId: 'of-240',
    cvId: 'cv-sarra-1',
    status: 'OFFERED',
    appliedAt: '2026-09-23T09:00:00Z',
    history: [
      { id: 'h-17', status: 'SUBMITTED', changedAt: '2026-09-23T09:00:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-18', status: 'UNDER_REVIEW', changedAt: '2026-09-24T10:00:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-19', status: 'PRESELECTED', changedAt: '2026-09-25T14:00:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-20', status: 'INTERVIEW', changedAt: '2026-09-27T09:30:00Z', changedByRole: 'RECRUITER' },
      { id: 'h-21', status: 'OFFERED', reason: 'Proposition transmise, en attente de réponse.', changedAt: '2026-09-30T11:00:00Z', changedByRole: 'RECRUITER' },
    ],
  },
  {
    id: 'ap-9',
    candidateId: 'cp-nour',
    offerId: 'of-245',
    cvId: 'cv-emna-1',
    status: 'WITHDRAWN',
    appliedAt: '2026-09-25T07:40:00Z',
    withdrawnAt: '2026-09-27T18:00:00Z',
    history: [
      { id: 'h-22', status: 'SUBMITTED', changedAt: '2026-09-25T07:40:00Z', changedByRole: 'CANDIDATE' },
      { id: 'h-23', status: 'WITHDRAWN', reason: 'Distance incompatible avec ma situation familiale.', changedAt: '2026-09-27T18:00:00Z', changedByRole: 'CANDIDATE' },
    ],
  },
]

export const INTERVIEWS: Interview[] = [
  { id: 'iv-1', applicationId: 'ap-4', type: 'VISIO', scheduledAt: '2026-10-03T10:00:00Z', durationMinutes: 60, locationOrUrl: 'https://meet.example.tn/telnet-tech', status: 'PLANIFIE' },
  { id: 'iv-2', applicationId: 'ap-8', type: 'PRESENTIEL', scheduledAt: '2026-09-29T09:00:00Z', durationMinutes: 45, locationOrUrl: 'Laboratoires Médis, Nabeul', status: 'REALISE', feedback: 'Maîtrise des déclarations sociales confirmée.' },
]

/* ------------------------------------------------------------------ */
/* Formations                                                          */
/* ------------------------------------------------------------------ */

export const TRAINING_PROGRAMS: TrainingProgram[] = [
  { id: 'tp-docker', organizationId: 'org-codeline', title: 'Docker et conteneurisation — les bases', description: 'Comprendre les images, les conteneurs et docker-compose. Déployer une application de bout en bout.', level: 'DEBUTANT', deliveryMode: 'HYBRIDE', status: 'PUBLISHED', durationHours: 24, priceTnd: 450, prerequisites: 'Savoir utiliser un terminal. Notions de base en développement.', contactEmail: 'formation@codeline.tn', skillIds: ['sk-docker'] },
  { id: 'tp-sql', organizationId: 'org-iset', title: 'SQL avancé pour l’analyse de données', description: 'Jointures complexes, fonctions de fenêtrage et optimisation des requêtes.', level: 'AVANCE', deliveryMode: 'PRESENTIEL', status: 'PUBLISHED', durationHours: 30, priceTnd: 380, prerequisites: 'Pratique courante des requêtes SQL simples.', contactEmail: 'fc@isetbz.tn', skillIds: ['sk-sql'] },
  { id: 'tp-powerbi', organizationId: 'org-codeline', title: 'Power BI — tableaux de bord métier', description: 'Modélisation, DAX et publication de rapports.', level: 'INTERMEDIAIRE', deliveryMode: 'DISTANCIEL', status: 'PUBLISHED', durationHours: 21, prerequisites: 'Bonne maîtrise d’Excel.', contactEmail: 'formation@codeline.tn', skillIds: ['sk-powerbi', 'sk-excel'] },
  { id: 'tp-react', organizationId: 'org-codeline', title: 'React — développement d’interfaces', description: 'Composants, état, routage et appels API.', level: 'INTERMEDIAIRE', deliveryMode: 'HYBRIDE', status: 'PUBLISHED', durationHours: 40, priceTnd: 700, prerequisites: 'JavaScript courant.', contactEmail: 'formation@codeline.tn', skillIds: ['sk-react', 'sk-js'] },
  { id: 'tp-soudure', organizationId: 'org-iset', title: 'Soudure — certification des procédés', description: 'Préparation à la qualification des soudeurs.', level: 'AVANCE', deliveryMode: 'PRESENTIEL', status: 'PUBLISHED', durationHours: 60, priceTnd: 0, prerequisites: 'Expérience pratique en atelier.', contactEmail: 'fc@isetbz.tn', skillIds: ['sk-soudure'] },
  { id: 'tp-paie', organizationId: 'org-iset', title: 'Gestion de la paie en Tunisie', description: 'Réglementation, bulletins et déclarations sociales.', level: 'INTERMEDIAIRE', deliveryMode: 'PRESENTIEL', status: 'DRAFT', durationHours: 28, prerequisites: 'Bases en comptabilité.', contactEmail: 'fc@isetbz.tn', skillIds: ['sk-paie'] },
  { id: 'tp-ml', organizationId: 'org-codeline', title: 'Introduction au machine learning', description: 'Apprentissage supervisé avec scikit-learn.', level: 'INTERMEDIAIRE', deliveryMode: 'DISTANCIEL', status: 'ARCHIVED', durationHours: 35, priceTnd: 600, prerequisites: 'Python intermédiaire.', contactEmail: 'formation@codeline.tn', skillIds: ['sk-ml', 'sk-python'] },
]

export const TRAINING_SESSIONS: TrainingSession[] = [
  { id: 'ts-1', programId: 'tp-docker', startDate: '2026-10-20', endDate: '2026-11-07', capacity: 18, locationOrUrl: 'Lac 2, Tunis + classe virtuelle', registrationDeadline: '2026-10-15', status: 'OUVERTE' },
  { id: 'ts-2', programId: 'tp-docker', startDate: '2026-12-01', endDate: '2026-12-19', capacity: 18, locationOrUrl: 'Lac 2, Tunis + classe virtuelle', registrationDeadline: '2026-11-25', status: 'PLANIFIEE' },
  { id: 'ts-3', programId: 'tp-sql', startDate: '2026-10-06', endDate: '2026-10-24', capacity: 14, locationOrUrl: 'ISET Bizerte', registrationDeadline: '2026-10-02', status: 'COMPLETE' },
  { id: 'ts-4', programId: 'tp-powerbi', startDate: '2026-11-03', endDate: '2026-11-21', capacity: 25, locationOrUrl: 'Classe virtuelle', registrationDeadline: '2026-10-28', status: 'OUVERTE' },
  { id: 'ts-5', programId: 'tp-react', startDate: '2026-10-13', endDate: '2026-11-28', capacity: 16, locationOrUrl: 'Lac 2, Tunis', registrationDeadline: '2026-10-08', status: 'OUVERTE' },
  { id: 'ts-6', programId: 'tp-soudure', startDate: '2026-09-01', endDate: '2026-09-26', capacity: 12, locationOrUrl: 'ISET Bizerte — atelier', registrationDeadline: '2026-08-25', status: 'TERMINEE' },
]

export const TRAINING_ENROLLMENTS: TrainingEnrollment[] = [
  { id: 'te-1', sessionId: 'ts-1', candidateId: 'cp-emna', status: 'INSCRIT', enrolledAt: '2026-09-28T12:00:00Z', completionRate: 0 },
  { id: 'te-2', sessionId: 'ts-3', candidateId: 'cp-mehdi', status: 'EN_COURS', enrolledAt: '2026-09-15T09:00:00Z', completionRate: 40 },
  { id: 'te-3', sessionId: 'ts-6', candidateId: 'cp-hamza', status: 'TERMINE', enrolledAt: '2026-08-20T10:00:00Z', completionRate: 100 },
  { id: 'te-4', sessionId: 'ts-5', candidateId: 'cp-yassine', status: 'INSCRIT', enrolledAt: '2026-09-30T08:00:00Z', completionRate: 0 },
  { id: 'te-5', sessionId: 'ts-1', candidateId: 'cp-mehdi', status: 'INSCRIT', enrolledAt: '2026-09-29T16:20:00Z', completionRate: 0 },
]

/* ------------------------------------------------------------------ */
/* Imports et audit                                                    */
/* ------------------------------------------------------------------ */

export const DATA_SOURCES: DataSource[] = [
  { id: 'src-aneti', name: 'ANETI Open Data', type: 'API', baseUrl: 'https://api.aneti.tn', isAuthorized: true },
  { id: 'src-partenaire', name: 'Partenaire RH', type: 'CSV', isAuthorized: true },
  { id: 'src-abc', name: 'Entreprise ABC', type: 'MANUAL_FILE', isAuthorized: false },
]

export const IMPORT_BATCHES: ImportBatch[] = [
  { id: 'ib-1', sourceId: 'src-aneti', checksum: 'a7f3c9e1b240', status: 'COMPLETED', startedAt: '2026-09-29T05:00:00Z', completedAt: '2026-09-29T05:12:00Z', addedCount: 700, updatedCount: 150, unchangedCount: 130, rejectedCount: 20 },
  { id: 'ib-2', sourceId: 'src-partenaire', checksum: 'd41d8cd98f00', status: 'COMPLETED', startedAt: '2026-09-30T05:00:00Z', completedAt: '2026-09-30T05:03:00Z', addedCount: 90, updatedCount: 0, unchangedCount: 0, rejectedCount: 10 },
  { id: 'ib-3', sourceId: 'src-aneti', checksum: 'b92f04ac7731', status: 'RUNNING', startedAt: '2026-10-01T05:00:00Z', addedCount: 212, updatedCount: 44, unchangedCount: 61, rejectedCount: 3 },
]

export const IMPORT_ROWS: ImportRow[] = [
  { id: 'ir-1', batchId: 'ib-2', rowNumber: 1, externalId: 'ANETI-1001', status: 'ADDED' },
  { id: 'ir-2', batchId: 'ib-2', rowNumber: 2, externalId: 'ANETI-1002', status: 'UPDATED' },
  { id: 'ir-3', batchId: 'ib-2', rowNumber: 3, status: 'REJECTED', errorCode: 'MISSING_EXTERNAL_ID', errorMessage: 'Identifiant externe absent : la ligne ne peut pas être dédoublonnée.' },
  { id: 'ir-4', batchId: 'ib-2', rowNumber: 4, externalId: 'ANETI-1004', status: 'REJECTED', errorCode: 'INVALID_DATE', errorMessage: 'Date de clôture antérieure à la date de publication.' },
  { id: 'ir-5', batchId: 'ib-2', rowNumber: 5, externalId: 'ANETI-1005', status: 'ADDED' },
  { id: 'ir-6', batchId: 'ib-2', rowNumber: 6, externalId: 'ANETI-1006', status: 'UNCHANGED' },
  { id: 'ir-7', batchId: 'ib-2', rowNumber: 7, externalId: 'ANETI-1007', status: 'REJECTED', errorCode: 'UNKNOWN_SKILL', errorMessage: 'Compétence « dev web » non normalisée dans le référentiel.' },
]

export const AUDIT_LOGS: AuditLog[] = [
  { id: 'al-1', actorLabel: 'Sofiane Mabrouk', actorKind: 'UTILISATEUR', action: 'Changement de statut de candidature', entityType: 'Candidature', entityId: 'ap-8', createdAt: '2026-09-30T11:00:12Z', ipAddress: '197.14.xx.xx' },
  { id: 'al-2', actorLabel: 'Agent conversationnel', actorKind: 'AGENT_IA', action: 'Dépôt de candidature après confirmation du candidat', entityType: 'Candidature', entityId: 'ap-2', createdAt: '2026-09-26T16:10:04Z' },
  { id: 'al-3', actorLabel: 'Rania Saidi', actorKind: 'UTILISATEUR', action: 'Vérification d’organisation', entityType: 'Organisation', entityId: 'org-medis', createdAt: '2026-09-30T09:41:00Z', ipAddress: '41.226.xx.xx' },
  { id: 'al-4', actorLabel: 'Pipeline d’import', actorKind: 'SYSTEME', action: 'Lot d’import terminé — 90 ajoutées, 10 rejetées', entityType: 'Lot d’import', entityId: 'ib-2', createdAt: '2026-09-30T05:03:00Z' },
  { id: 'al-6', actorLabel: 'Agent conversationnel', actorKind: 'AGENT_IA', action: 'Action bloquée — offre clôturée entre la préparation et la confirmation', entityType: 'Offre', entityId: 'of-199', createdAt: '2026-09-11T10:02:00Z' },
  { id: 'al-7', actorLabel: 'Rania Saidi', actorKind: 'UTILISATEUR', action: 'Ajout d’un alias au référentiel des compétences', entityType: 'Compétence', entityId: 'sk-docker', createdAt: '2026-09-28T13:10:00Z', ipAddress: '41.226.xx.xx' },
]

export const NOTIFICATIONS: Notification[] = [
  { id: 'nt-1', userId: 'u-emna', title: 'Votre candidature a été présélectionnée', body: 'COFAT Bizerte — Analyste données de production.', createdAt: '2026-09-24T10:40:00Z' },
  { id: 'nt-2', userId: 'u-emna', title: 'Une formation correspond à un écart identifié', body: 'Docker et conteneurisation — session du 20 octobre, inscriptions ouvertes.', createdAt: '2026-09-27T08:00:00Z', readAt: '2026-09-27T19:00:00Z' },
  { id: 'nt-3', userId: 'u-emna', title: 'Votre dossier est passé en examen', body: 'TelNet Ariana — Développeur junior.', createdAt: '2026-09-29T09:15:00Z' },
  { id: 'nt-4', userId: 'u-sofiane', title: 'Nouvelle candidature reçue', body: 'Yassine Gharbi — Développeur junior (OF-218).', createdAt: '2026-09-29T19:45:00Z' },
]

/** Indicateurs régionaux agrégés servis au ministère. */
export const REGIONAL_STATS = [
  { governorate: 'Tunis', offers: 1240, applications: 8930, hires: 412, trainings: 186 },
  { governorate: 'Ariana', offers: 684, applications: 5120, hires: 231, trainings: 98 },
  { governorate: 'Sfax', offers: 596, applications: 4310, hires: 198, trainings: 142 },
  { governorate: 'Sousse', offers: 471, applications: 3380, hires: 164, trainings: 77 },
  { governorate: 'Nabeul', offers: 388, applications: 2640, hires: 121, trainings: 64 },
  { governorate: 'Bizerte', offers: 302, applications: 2190, hires: 96, trainings: 58 },
  { governorate: 'Monastir', offers: 277, applications: 1870, hires: 88, trainings: 51 },
  { governorate: 'Gabès', offers: 164, applications: 1120, hires: 47, trainings: 29 },
  { governorate: 'Kairouan', offers: 132, applications: 980, hires: 34, trainings: 41 },
  { governorate: 'Médenine', offers: 118, applications: 760, hires: 29, trainings: 22 },
]

/** Compétences : demande du marché face à l'offre de formation disponible. */
export const SKILL_DEMAND = [
  { skillId: 'sk-sql', demand: 412, trainingSeats: 180 },
  { skillId: 'sk-python', demand: 388, trainingSeats: 145 },
  { skillId: 'sk-docker', demand: 301, trainingSeats: 54 },
  { skillId: 'sk-js', demand: 276, trainingSeats: 210 },
  { skillId: 'sk-excel', demand: 265, trainingSeats: 320 },
  { skillId: 'sk-soudure', demand: 198, trainingSeats: 36 },
  { skillId: 'sk-elec', demand: 174, trainingSeats: 88 },
  { skillId: 'sk-couture', demand: 162, trainingSeats: 44 },
  { skillId: 'sk-paie', demand: 121, trainingSeats: 60 },
  { skillId: 'sk-powerbi', demand: 118, trainingSeats: 95 },
]
