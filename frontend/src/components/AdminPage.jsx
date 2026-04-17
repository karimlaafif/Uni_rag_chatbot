import { useState, useEffect, useRef } from 'react'
import { uploadDocument, getKnowledgeStatus, runBenchmark, getBenchmarkResults } from '../api.js'
import './AdminPage.css'

const DEPARTMENTS = [
  'scolarite',
  'bibliotheque',
  'residence',
  'sport',
  'informatique',
  'mathematiques',
  'physique',
  'chimie',
  'biologie',
  'economie',
  'droit',
  'medecine',
  'pharmacie',
  'autre',
]

const ACCESS_LEVELS = [
  { value: 'public', label: '🌐 Public',           desc: 'Visible par tous les utilisateurs' },
  { value: 'staff',  label: '🏫 Personnel',         desc: 'Visible par le personnel et les admins' },
  { value: 'admin',  label: '⚙️ Administrateurs',   desc: 'Visible uniquement par les admins' },
]

/* ── Statut badge ──────────────────────────────────────────────────────── */
function StatusBadge({ status }) {
  const config = {
    idle:     { label: 'Opérationnel', color: '#10B981', bg: '#DCFCE7' },
    indexing: { label: 'Indexation…',  color: '#D97706', bg: '#FEF9C3' },
    error:    { label: 'Erreur',        color: '#DC2626', bg: '#FEE2E2' },
  }

  const c = config[status] || config.idle
  return (
    <span className="status-badge" style={{ color: c.color, background: c.bg }}>
      <span className="status-dot" style={{ background: c.color, animation: status === 'indexing' ? 'pulse 1s infinite' : 'none' }} />
      {c.label}
    </span>
  )
}

/* ── Section Upload de document ──────────────────────────────────────────── */
function UploadSection({ onRefreshStatus }) {
  const [file, setFile]           = useState(null)
  const [department, setDept]     = useState('scolarite')
  const [accessLevel, setAccess]  = useState('public')
  const [uploading, setUploading] = useState(false)
  const [result, setResult]       = useState(null)   // { ok, message }
  const fileRef = useRef(null)

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (f) setFile(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f) { setFile(f); e.currentTarget.classList.remove('dragover') }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setResult(null)

    try {
      const res = await uploadDocument(file, department, accessLevel)
      setResult({ ok: true, message: res.message || 'Document mis en file d\'attente avec succès.' })
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
      onRefreshStatus()
    } catch (err) {
      setResult({ ok: false, message: `Erreur : ${err.message}` })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="admin-card">
      <div className="card-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <h2>Ajouter un document</h2>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        {/* Zone de dépôt de fichier */}
        <div
          className={`dropzone ${file ? 'has-file' : ''}`}
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('dragover') }}
          onDragLeave={(e) => e.currentTarget.classList.remove('dragover')}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.doc,.docx,.txt,.md,.pptx,.xlsx,.csv"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          {file ? (
            <div className="file-info">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                   fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <div>
                <p className="file-name">{file.name}</p>
                <p className="file-size">{(file.size / 1024).toFixed(1)} Ko</p>
              </div>
              <button
                type="button"
                className="btn-remove-file"
                onClick={(e) => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = '' }}
              >✕</button>
            </div>
          ) : (
            <div className="dropzone-placeholder">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24"
                   fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <p>Glissez-déposez un fichier ou <span>cliquez pour parcourir</span></p>
              <p className="dropzone-formats">PDF, DOCX, TXT, MD, PPTX, XLSX, CSV</p>
            </div>
          )}
        </div>

        {/* Département */}
        <div className="form-group">
          <label htmlFor="dept">Département / Service</label>
          <select id="dept" value={department} onChange={e => setDept(e.target.value)}>
            {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        {/* Niveau d'accès */}
        <div className="form-group">
          <label>Niveau d'accès</label>
          <div className="access-options">
            {ACCESS_LEVELS.map(al => (
              <label key={al.value} className={`access-option ${accessLevel === al.value ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="access_level"
                  value={al.value}
                  checked={accessLevel === al.value}
                  onChange={() => setAccess(al.value)}
                  style={{ display: 'none' }}
                />
                <span className="access-label">{al.label}</span>
                <span className="access-desc">{al.desc}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Résultat */}
        {result && (
          <div className={`upload-result ${result.ok ? 'success' : 'error'}`}>
            {result.ok
              ? <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              : <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
            }
            {result.message}
          </div>
        )}

        <button
          type="submit"
          className="btn-primary"
          disabled={!file || uploading}
        >
          {uploading ? 'Envoi en cours…' : 'Indexer le document'}
        </button>
      </form>
    </div>
  )
}

/* ── Section Statut d'indexation ─────────────────────────────────────────── */
function StatusSection() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const s = await getKnowledgeStatus()
      setStatus(s)
    } catch {
      setStatus({ status: 'error', last_update: '—' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Rafraîchissement automatique si l'indexation est en cours
    const interval = setInterval(() => {
      if (status?.status === 'indexing') fetchStatus()
    }, 4000)
    return () => clearInterval(interval)
  }, [status?.status])

  return (
    <div className="admin-card">
      <div className="card-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <h2>Statut de la base de connaissances</h2>
        <button className="btn-refresh" onClick={fetchStatus} disabled={loading} title="Rafraîchir">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
               style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }}>
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.33"/>
          </svg>
        </button>
      </div>

      {status ? (
        <div className="status-grid">
          <div className="status-row">
            <span className="status-label">État</span>
            <StatusBadge status={status.status} />
          </div>
          <div className="status-row">
            <span className="status-label">Dernière mise à jour</span>
            <span className="status-value">
              {status.last_update === 'jamais' || !status.last_update
                ? 'Jamais'
                : new Date(status.last_update).toLocaleString('fr-FR')}
            </span>
          </div>
        </div>
      ) : (
        <p className="status-loading">Chargement…</p>
      )}
    </div>
  )
}

/* ── Section Benchmark RAGAS ─────────────────────────────────────────────── */
function BenchmarkSection() {
  const [jobId, setJobId]     = useState(null)
  const [result, setResult]   = useState(null)
  const [running, setRunning] = useState(false)
  const pollRef = useRef(null)

  const handleRun = async () => {
    setRunning(true)
    setResult(null)

    try {
      const res = await runBenchmark()
      setJobId(res.job_id)

      // Polling toutes les 5 secondes
      pollRef.current = setInterval(async () => {
        try {
          const r = await getBenchmarkResults(res.job_id)
          if (r.result !== 'running') {
            clearInterval(pollRef.current)
            setResult(r.result)
            setRunning(false)
          }
        } catch { /* ignore les erreurs de poll */ }
      }, 5000)
    } catch (err) {
      setResult({ error: err.message })
      setRunning(false)
    }
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  return (
    <div className="admin-card">
      <div className="card-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/>
        </svg>
        <h2>Benchmark RAGAS</h2>
      </div>

      <p className="card-desc">
        Lance une évaluation automatique de la qualité du RAG (Faithfulness, Context Precision, Answer Relevancy).
      </p>

      <button
        className="btn-primary"
        onClick={handleRun}
        disabled={running}
      >
        {running ? (
          <>
            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                 style={{ animation: 'spin 1s linear infinite' }}>
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            Benchmark en cours…
          </>
        ) : 'Lancer le benchmark'}
      </button>

      {jobId && (
        <p className="job-id">Job ID : <code>{jobId}</code></p>
      )}

      {result && !result.error && (
        <div className="benchmark-results">
          <h3>Résultats</h3>
          <div className="metrics-grid">
            {Object.entries(result).map(([key, val]) => (
              <div key={key} className="metric-card">
                <span className="metric-name">{key.replace(/_/g, ' ')}</span>
                <span className="metric-value">
                  {typeof val === 'number' ? (val * 100).toFixed(1) + '%' : String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result?.error && (
        <div className="upload-result error">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          {result.error}
        </div>
      )}
    </div>
  )
}

/* ── Page Admin principale ───────────────────────────────────────────────── */
export default function AdminPage() {
  const [statusKey, setStatusKey] = useState(0)

  const refreshStatus = () => setStatusKey(k => k + 1)

  return (
    <div className="admin-page">
      <div className="admin-container">
        <div className="admin-header">
          <h1>Panneau d'administration</h1>
          <p>Gérez la base de connaissances et surveillez les performances du système.</p>
        </div>

        <div className="admin-grid">
          <div className="admin-col-left">
            <UploadSection onRefreshStatus={refreshStatus} />
          </div>
          <div className="admin-col-right">
            <StatusSection key={statusKey} />
            <BenchmarkSection />
          </div>
        </div>
      </div>
    </div>
  )
}
