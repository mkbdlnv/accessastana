/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the API, default "/api" (proxied to the FastAPI service). */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
