// Placement: frontend/tests/importRejections.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { IMPORT_ROW_STATUS_LABEL, IMPORT_REJECTION_LABEL, labelFor } from '../src/lib/format.ts'

test('every rejection code the import pipeline emits has a French reason', () => {
  assert.deepEqual(IMPORT_REJECTION_LABEL, {
    OFFER_CLOSED: 'Offre fermée ou expirée',
    MISSING_EXTERNAL_ID: 'Identifiant externe absent',
    INVALID_EXTERNAL_ID: 'Identifiant externe trop long',
    MISSING_TITLE: 'Titre absent',
    MISSING_DESCRIPTION: 'Description absente',
    INVALID_OFFER_URL: 'Lien de l’offre invalide',
    VALIDATION_ERROR: 'Données invalides',
  })
})

test('a rejection code the admin page does not know shows a fallback, never the raw code', () => {
  assert.equal(labelFor(IMPORT_REJECTION_LABEL, 'SOMETHING_NEW', 'Autre motif'), 'Autre motif')
  assert.equal(labelFor(IMPORT_REJECTION_LABEL, null), 'Non renseigné')
})

test('row statuses are shown in French', () => {
  assert.deepEqual(IMPORT_ROW_STATUS_LABEL, { ADDED: 'Ajoutée', UPDATED: 'Mise à jour', UNCHANGED: 'Inchangée', REJECTED: 'Rejetée' })
})
