import assert from 'node:assert/strict'
import test from 'node:test'
import {
  CONTRACT_OPTIONS,
  EXPERIENCE_OPTIONS,
  apiErrorMessage,
  contractLabel,
  experienceLabel,
  formatDateTime,
  formatPrice,
  formatTunisDateTime,
  skillLabel,
} from '../src/lib/format.ts'

test('one shared contract list is offered by the form and the filter', () => {
  assert.deepEqual(CONTRACT_OPTIONS, ['CDI', 'CDD', 'SIVP', 'KARAMA', 'INTERNSHIP', 'FREELANCE', 'SEASONAL'])
})

test('contract codes from the app and from imports share one French label', () => {
  assert.equal(contractLabel('INTERNSHIP'), 'Stage')
  assert.equal(contractLabel('SEASONAL'), 'Saisonnier')
  assert.equal(contractLabel('FULL_TIME'), 'Temps plein')
  assert.equal(contractLabel('PART_TIME'), 'Temps partiel')
})

test('unknown or missing contract values never show a raw code', () => {
  assert.equal(contractLabel(''), 'Non renseigné')
  assert.equal(contractLabel('XYZ'), 'Autre')
})

test('experience uses the site labels as both value and label', () => {
  assert.deepEqual(EXPERIENCE_OPTIONS, ['Débutant', '0 à 1 an', '1 à 3 ans', '3 à 5 ans', '5 à 10 ans'])
  assert.equal(experienceLabel('1 à 3 ans'), '1 à 3 ans')
  assert.equal(experienceLabel(''), 'Non renseigné')
})

test('known API errors are translated and unknown ones keep the original text', () => {
  assert.equal(apiErrorMessage('permission_denied', 'You do not have permission.'), 'Action non autorisée pour votre compte.')
  assert.equal(apiErrorMessage('validation_error', 'Request validation failed.'), 'Les informations saisies ne sont pas valides.')
  assert.equal(apiErrorMessage('validation_error', 'Request validation failed.', { title: ['Required.'] }), 'Titre : ce champ est obligatoire.')
  assert.equal(apiErrorMessage('request_error', 'Boom'), 'Une erreur est survenue. (Boom)')
})

test('field names without a French label fall back to a generic French label', () => {
  assert.match(apiErrorMessage('validation_error', 'Request validation failed.', { mystery_field: ['Odd.'] }), /^Champ : /)
})

test('interview times show the Tunis wall clock with its zone label', () => {
  assert.equal(formatTunisDateTime('2026-10-24T09:00:00Z'), '24 oct. 2026, 10:00 UTC+1')
})

test('date-times read on a 24-hour clock', () => {
  assert.equal(formatDateTime('2026-11-07T14:53:00'), '07 nov. 2026, 14:53')
  assert.equal(formatDateTime('2026-11-07T00:05:00'), '07 nov. 2026, 00:05')
})

test('prices: free, whole and decimal amounts share one format', () => {
  assert.equal(formatPrice('0.00'), 'Gratuit')
  assert.equal(formatPrice(0), 'Gratuit')
  assert.equal(formatPrice('600.00'), '600 TND')
  assert.equal(formatPrice('1250.50'), '1\u202f250,5 TND')
  assert.equal(formatPrice(undefined), 'Non renseigné')
})

test('skill labels get a capital first letter only', () => {
  assert.equal(skillLabel('data mining'), 'Data mining')
  assert.equal(skillLabel('utilise machine learning'), 'Utilise machine learning')
  assert.equal(skillLabel('Python'), 'Python')
  assert.equal(skillLabel('SQL'), 'SQL')
  assert.equal(skillLabel('écrire du code'), 'Écrire du code')
  assert.equal(skillLabel(''), '')
})
