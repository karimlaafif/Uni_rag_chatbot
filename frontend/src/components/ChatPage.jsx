import { useState, useRef, useEffect, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { sendChat } from '../api.js'
import './ChatPage.css'

/* ── Rôles disponibles ──────────────────────────────────────────────────── */
const ROLES = [
  { value: 'student', label: 'Étudiant(e)',    emoji: '🎓' },
  { value: 'staff',   label: 'Personnel',      emoji: '🏫' },
  { value: 'admin',   label: 'Administrateur', emoji: '⚙️' },
]

/* ── Composant TypingDots ───────────────────────────────────────────────── */
function TypingDots() {
  return (
    <div className="typing-indicator">
      <span /><span /><span />
    </div>
  )
}

/* ── Composant SourcesPanel ─────────────────────────────────────────────── */
function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="sources-panel">
      <button className="sources-toggle" onClick={() => setOpen(o => !o)}>
        <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        {sources.length} source{sources.length > 1 ? 's' : ''} citée{sources.length > 1 ? 's' : ''}
        <svg
          xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24"
          fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <ul className="sources-list">
          {sources.map((src, i) => (
            <li key={i} className="source-item">
              <span className="source-index">[{i + 1}]</span>
              <div className="source-content">
                <span className="source-title">
                  {src.url
                    ? <a href={src.url} target="_blank" rel="noopener noreferrer">{src.title || src.url}</a>
                    : src.title || `Source ${i + 1}`
                  }
                </span>
                {src.access_level && (
                  <span className={`source-badge badge-${src.access_level}`}>{src.access_level}</span>
                )}
                {src.rerank_score != null && src.rerank_score > 0 && (
                  <span className="source-score">score: {src.rerank_score.toFixed(2)}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ── Composant MessageBubble ────────────────────────────────────────────── */
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="avatar assistant-avatar">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4l3 3"/>
          </svg>
        </div>
      )}

      <div className="bubble-container">
        {/* Image preview si présente */}
        {msg.imagePreview && (
          <div className="bubble-image-preview">
            <img src={msg.imagePreview} alt="Image envoyée" />
          </div>
        )}

        {/* Bulle texte */}
        <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
          {msg.loading ? <TypingDots /> : <p>{msg.content}</p>}
        </div>

        {/* Métadonnées (latence) */}
        {!isUser && !msg.loading && msg.latency_ms != null && (
          <div className="bubble-meta">
            ⚡ {msg.latency_ms} ms &nbsp;·&nbsp; {msg.model || 'ollama'}
          </div>
        )}

        {/* Sources */}
        {!isUser && !msg.loading && <SourcesPanel sources={msg.sources} />}
      </div>

      {isUser && (
        <div className="avatar user-avatar">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </div>
      )}
    </div>
  )
}

/* ── Page principale Chat ───────────────────────────────────────────────── */
export default function ChatPage() {
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [userRole, setUserRole]     = useState('student')
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [image, setImage]           = useState(null)   // { file, base64, preview }
  const [sessionId]                 = useState(() => uuidv4())

  const bottomRef    = useRef(null)
  const fileInputRef = useRef(null)
  const textareaRef  = useRef(null)

  /* Auto-scroll vers le bas */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /* Message de bienvenue */
  useEffect(() => {
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: 'Bonjour ! Je suis l\'assistant universitaire de l\'Université Ibn Zohr. Comment puis-je vous aider aujourd\'hui ? أهلاً، كيف يمكنني مساعدتك؟',
      sources: [],
    }])
  }, [])

  /* Lecture image → base64 */
  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Veuillez sélectionner un fichier image valide.')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target.result
      // Le backend attend juste le contenu base64, sans le préfixe "data:…"
      const base64 = dataUrl.split(',')[1]
      setImage({ file, base64, preview: dataUrl })
    }
    reader.readAsDataURL(file)
  }

  /* Auto-resize textarea */
  const handleInputChange = (e) => {
    setInput(e.target.value)
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
    }
  }

  /* Envoi du message */
  const handleSend = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed && !image) return
    if (loading) return

    setError(null)
    const msgId = uuidv4()

    // Ajoute le message utilisateur
    const userMsg = {
      id: msgId,
      role: 'user',
      content: trimmed || '📷 Image envoyée',
      imagePreview: image?.preview || null,
    }

    // Ajoute un placeholder "en cours de chargement" pour l'assistant
    const loadingMsg = { id: `loading-${msgId}`, role: 'assistant', loading: true, content: '', sources: [] }

    setMessages(prev => [...prev, userMsg, loadingMsg])
    setInput('')
    setImage(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setLoading(true)

    try {
      const res = await sendChat({
        query: trimmed || 'Décris cette image',
        session_id: sessionId,
        user_role: userRole,
        image_base64: image?.base64 || null,
      })

      setMessages(prev => prev.map(m =>
        m.id === `loading-${msgId}`
          ? {
              id: uuidv4(),
              role: 'assistant',
              content: res.answer,
              sources: res.sources || [],
              latency_ms: res.latency_ms,
              model: res.model,
              loading: false,
            }
          : m
      ))
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== `loading-${msgId}`))
      setError(`Erreur : ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [input, image, loading, sessionId, userRole])

  /* Envoi sur Entrée (Shift+Entrée = saut de ligne) */
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /* Réinitialiser la conversation */
  const handleClear = () => {
    setMessages([{
      id: 'welcome-new',
      role: 'assistant',
      content: 'Nouvelle conversation commencée. Comment puis-je vous aider ?',
      sources: [],
    }])
    setError(null)
  }

  return (
    <div className="chat-page">
      {/* ── Barre de contrôle ──────────────────────────────────────────── */}
      <div className="chat-controls">
        <div className="role-selector">
          <label htmlFor="role-select">Profil :</label>
          <select
            id="role-select"
            value={userRole}
            onChange={e => setUserRole(e.target.value)}
            disabled={loading}
          >
            {ROLES.map(r => (
              <option key={r.value} value={r.value}>
                {r.emoji} {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="session-info">
          <span className="session-dot" />
          <span>Session active</span>
        </div>

        <button className="btn-clear" onClick={handleClear} title="Nouvelle conversation">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.33"/>
          </svg>
          Nouveau chat
        </button>
      </div>

      {/* ── Zone de messages ────────────────────────────────────────────── */}
      <div className="messages-area">
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* ── Bandeau d'erreur ────────────────────────────────────────────── */}
      {error && (
        <div className="error-banner">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* ── Barre de saisie ─────────────────────────────────────────────── */}
      <div className="input-area">
        {/* Preview image sélectionnée */}
        {image && (
          <div className="image-preview-bar">
            <img src={image.preview} alt="Aperçu" />
            <span>{image.file.name}</span>
            <button
              className="btn-remove-image"
              onClick={() => { setImage(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
            >
              ✕
            </button>
          </div>
        )}

        <div className="input-row">
          {/* Bouton upload image */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleImageSelect}
            id="image-file-input"
          />
          <button
            className={`btn-icon btn-image-upload ${image ? 'active' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            title="Joindre une image"
            disabled={loading}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
          </button>

          {/* Zone de texte */}
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder="Posez votre question… (Entrée pour envoyer, Maj+Entrée pour sauter une ligne)"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={loading}
          />

          {/* Bouton envoyer */}
          <button
            className="btn-send"
            onClick={handleSend}
            disabled={loading || (!input.trim() && !image)}
            title="Envoyer"
          >
            {loading
              ? <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                     style={{ animation: 'spin 1s linear infinite' }}>
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
              : <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
            }
          </button>
        </div>
      </div>
    </div>
  )
}
