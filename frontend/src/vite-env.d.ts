/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL de base de l'API backend, ex. https://api.mahara-match.tn/v1 */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
