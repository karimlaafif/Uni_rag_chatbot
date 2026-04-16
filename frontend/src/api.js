/**
 * api.js — Couche d'appels vers le backend FastAPI RAG
 *
 * En dev  : Vite proxifie /api/* → http://localhost:8000/*
 * En prod : La variable VITE_API_BASE_URL peut surcharger la base URL
 *           (laisser vide pour utiliser le proxy nginx)
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

/**
 * Envoie un message au chatbot RAG.
 *
 * @param {Object} params
 * @param {string} params.query        - La question de l'utilisateur
 * @param {string} params.session_id   - UUID de session (persistance mémoire)
 * @param {string} params.user_role    - 'student' | 'staff' | 'admin'
 * @param {string|null} params.image_base64 - Image en base64 (multimodal)
 * @returns {Promise<ChatResponse>}
 */
export async function sendChat({ query, session_id, user_role, image_base64 = null }) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id, user_role, image_base64 }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }

  return res.json()
}

/**
 * Upload un document dans la base de connaissances.
 *
 * @param {File}   file          - Fichier à indexer (PDF, DOCX, TXT…)
 * @param {string} department    - Département/service (ex: "scolarite")
 * @param {string} access_level  - Niveau d'accès : 'public' | 'staff' | 'admin'
 * @returns {Promise<{message: string}>}
 */
export async function uploadDocument(file, department, access_level) {
  const form = new FormData()
  form.append('file', file)
  form.append('department', department)
  form.append('access_level', access_level)

  const res = await fetch(`${API_BASE}/knowledge/update`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }

  return res.json()
}

/**
 * Récupère le statut de l'indexation des documents.
 *
 * @returns {Promise<{status: string, last_update: string}>}
 */
export async function getKnowledgeStatus() {
  const res = await fetch(`${API_BASE}/knowledge/status`)

  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`)
  }

  return res.json()
}

/**
 * Lance un benchmark RAGAS.
 *
 * @returns {Promise<{job_id: string, status: string}>}
 */
export async function runBenchmark() {
  const res = await fetch(`${API_BASE}/benchmark/run`, { method: 'POST' })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }

  return res.json()
}

/**
 * Récupère les résultats d'un job de benchmark.
 *
 * @param {string} job_id
 * @returns {Promise<{job_id: string, result: any}>}
 */
export async function getBenchmarkResults(job_id) {
  const res = await fetch(`${API_BASE}/benchmark/results/${job_id}`)

  if (!res.ok) {
    throw new Error(`Erreur ${res.status}`)
  }

  return res.json()
}
