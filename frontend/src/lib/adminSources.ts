// Placement: frontend/src/lib/adminSources.ts

export type SourceForm = { name: string; type: string; base_url: string; configuration: string }
export type SourceBody = { name: string; type: string; base_url?: string | null; configuration_json?: unknown }

/** Corps de POST/PATCH /data-sources/. Une URL vide devient null, une configuration vide devient {} (pour l’effacer), une configuration invalide arrête le formulaire. */
export function sourcePayload(form: SourceForm): { ok: true; body: SourceBody } | { ok: false; error: string } {
  const body: SourceBody = { name: form.name.trim(), type: form.type, base_url: form.base_url.trim() || null }
  body.configuration_json = {}
  if (form.configuration.trim()) {
    try { body.configuration_json = JSON.parse(form.configuration) }
    catch { return { ok: false, error: 'La configuration doit être un JSON valide.' } }
  }
  return { ok: true, body }
}

/** Seules les sources de collecte web autorisées se lancent depuis la page des imports (le navigateur tourne côté serveur). */
export const canLaunch = (source: { type: string; is_authorized: boolean }) => source.type === 'WEB_SCRAPING' && source.is_authorized
