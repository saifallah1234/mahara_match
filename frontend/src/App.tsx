import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout'
import { Button } from './components/ui'
import { ProtectedRoute, RoleRoute } from './components/authRoutes'
import { AuthProvider } from './state/auth'
import { CandidateProvider, useCandidate } from './state/candidate'
import { RecruiterProvider } from './state/recruiter'
import { TrainingProvider } from './state/training'

import { AdminProvider } from './state/admin'
import AdminComptes from './pages/admin/Comptes'
import AdminOrganisations from './pages/admin/Organisations'
import AdminDashboard from './pages/admin/Dashboard'
import AdminAudit from './pages/admin/Audit'
import AdminImports from './pages/admin/Imports'
import AdminReferentiels from './pages/admin/Referentiels'
import AdminOrganisationDetail from './pages/admin/OrganisationDetail'
import AdminBatchDetail from './pages/admin/BatchDetail'

import Landing from './pages/Landing'
import SignIn from './pages/SignIn'
import Register from './pages/Register'
import AdminOnboarding from './pages/AdminOnboarding'
import { Workspaces, NoAccess } from './pages/Workspaces'

import CandidatDashboard from './pages/candidat/Dashboard'
import CandidatProfil from './pages/candidat/Profil'
import CandidatCV from './pages/candidat/CV'
import CandidatOffres from './pages/candidat/Offres'
import CandidatOffreDetail from './pages/candidat/OffreDetail'
import CandidatCandidatures from './pages/candidat/Candidatures'
import CandidatFormations from './pages/candidat/Formations'
import CandidatAssistant from './pages/candidat/Assistant' 
import MockInterview from './pages/candidat/MockInterview'

import RecruteurDashboard from './pages/recruteur/Dashboard'
import RecruteurEntreprise from './pages/recruteur/Entreprise'
import RecruteurOffres from './pages/recruteur/Offres'
import RecruteurNouvelleOffre from './pages/recruteur/NouvelleOffre'
import RecruteurOffreDetail from './pages/recruteur/OffreDetail'
import RecruteurCandidatures from './pages/recruteur/Candidatures'
import RecruteurEntretiens from './pages/recruteur/Entretiens'
import RecruteurCandidats from './pages/recruteur/Candidats'
import RecruteurCandidatDetail from './pages/recruteur/CandidatDetail'
import RecruteurAssistant from './pages/recruteur/Assistant'

import { FormationDashboard, FormationOrganisme, FormationProgrammes, FormationSessions } from './pages/Formation'
import MinistereIndicateurs from './pages/ministere/Indicateurs'
import MinistereCompetences from './pages/ministere/Competences'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/connexion" element={<SignIn />} />
        <Route path="/inscription" element={<Register />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/espaces" element={<Workspaces />} />
          <Route path="/aucun-acces" element={<NoAccess />} />
          <Route element={<AppShell />}>
            <Route element={<RoleRoute role="CANDIDATE" />}>
              <Route element={<CandidateWorkspace />}>
                {/* Espace candidat */}
                <Route path="/candidat" element={<CandidatDashboard />} />
                <Route path="/candidat/profil" element={<CandidatProfil />} />
                <Route path="/candidat/cv" element={<CandidatCV />} />
                <Route path="/candidat/offres" element={<CandidatOffres />} />
                <Route path="/candidat/offres/:offerId" element={<CandidatOffreDetail />} />
                <Route path="/candidat/candidatures" element={<CandidatCandidatures />} />
                <Route path="/candidat/formations" element={<CandidatFormations />} />
                <Route path="/candidat/assistant" element={<CandidatAssistant />} />
                <Route path="/candidat/assistant/:conversationId" element={<CandidatAssistant />} />
                <Route path="/candidat/entretiens-blancs" element={<MockInterview />} />
                <Route path="/candidat/entretiens-blancs/:sessionId" element={<MockInterview />} />
              </Route>
            </Route>

            {/* Espace employeur */}
            <Route element={<RoleRoute role="RECRUITER" />}>
              <Route element={<RecruiterWorkspace />}>
                <Route path="/recruteur" element={<RecruteurDashboard />} />
                <Route path="/recruteur/entreprise" element={<RecruteurEntreprise />} />
                <Route path="/recruteur/offres" element={<RecruteurOffres />} />
                <Route path="/recruteur/offres/nouvelle" element={<RecruteurNouvelleOffre />} />
                <Route path="/recruteur/offres/:offerId" element={<RecruteurOffreDetail />} />
                <Route path="/recruteur/offres/:offerId/modifier" element={<RecruteurNouvelleOffre />} />
                <Route path="/recruteur/candidatures" element={<RecruteurCandidatures />} />
                <Route path="/recruteur/entretiens" element={<RecruteurEntretiens />} />
                <Route path="/recruteur/candidats" element={<RecruteurCandidats />} />
                <Route path="/recruteur/candidats/:candidateId" element={<RecruteurCandidatDetail />} />
                <Route path="/recruteur/assistant" element={<RecruteurAssistant />} />
                <Route path="/recruteur/assistant/:conversationId" element={<RecruteurAssistant />} />
              </Route>
            </Route>
            {/* Espace organisme de formation */}
            <Route element={<RoleRoute role="TRAINING_MANAGER" />}>
              <Route element={<TrainingWorkspace />}>
                <Route path="/formation" element={<FormationDashboard />} />
                <Route path="/formation/programmes" element={<FormationProgrammes />} />
                <Route path="/formation/sessions" element={<FormationSessions />} />
                <Route path="/formation/organisme" element={<FormationOrganisme />} />
              </Route>
            </Route>

            {/* Espace ministère */}
            <Route element={<RoleRoute role="MINISTRY_MANAGER" />}>
              <Route path="/ministere" element={<MinistereIndicateurs />} />
              <Route path="/ministere/competences" element={<MinistereCompetences />} />
            </Route>

            {/* Espace administration */}
            <Route element={<AdminWorkspace />}>

              <Route element={<RoleRoute role="ADMIN" />}>
                <Route path="/admin" element={<AdminDashboard />} />
                <Route path="/admin/comptes" element={<AdminComptes />} />
                <Route path="/admin/demandes" element={<AdminOnboarding />} />
                <Route path="/admin/organisations" element={<AdminOrganisations />} />
                <Route path="/admin/organisations/:id" element={<AdminOrganisationDetail />} />
                <Route path="/admin/referentiels" element={<AdminReferentiels />} />
                <Route path="/admin/imports" element={<AdminImports />} />
                <Route path="/admin/imports/batches/:id" element={<AdminBatchDetail />} />
                <Route path="/admin/audit" element={<AdminAudit />} />
              </Route>
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

function CandidateWorkspace() {
  return <CandidateProvider><CandidateWorkspaceContent /></CandidateProvider>
}

function CandidateWorkspaceContent() {
  const { loading, error, message, profile, clearMessage, reload } = useCandidate()
  return <>
    {loading && <div role="status" className="mx-auto max-w-5xl p-5">Chargement de votre espace…</div>}
    {error && <div role="alert" className="mx-auto max-w-5xl p-5 text-coral">{error} <Button size="sm" variant="secondaire" onClick={() => void reload()}>Réessayer</Button></div>}
    {message && <div role="status" className="mx-auto max-w-5xl p-5 text-teal">{message} <Button size="sm" variant="discret" onClick={clearMessage}>Fermer</Button></div>}
    {(profile || (!loading && !error)) && <Outlet />}
  </>
}
function RecruiterWorkspace() {
  return <RecruiterProvider><Outlet /></RecruiterProvider>
}
function TrainingWorkspace() {
  return <TrainingProvider><Outlet /></TrainingProvider>
}

function AdminWorkspace() {
  return <AdminProvider><Outlet /></AdminProvider>
}