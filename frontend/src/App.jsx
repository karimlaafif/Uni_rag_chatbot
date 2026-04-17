import { useState } from 'react'
import ChatPage from './components/ChatPage.jsx'
import AdminPage from './components/AdminPage.jsx'
import './App.css'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="app-shell">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-brand">
          <div className="header-logo">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" width="36" height="36">
              <rect width="40" height="40" rx="10" fill="white" fillOpacity="0.2"/>
              <text x="50%" y="55%" dominantBaseline="middle" textAnchor="middle"
                    fontSize="18" fontWeight="bold" fill="white" fontFamily="serif">
                UIZ
              </text>
            </svg>
          </div>
          <div className="header-title">
            <span className="header-main">Assistant Universitaire</span>
            <span className="header-sub">Université Ibn Zohr — Agadir</span>
          </div>
        </div>

        <nav className="header-nav">
          <button
            className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            Chat
          </button>
          <button
            className={`nav-tab ${activeTab === 'admin' ? 'active' : ''}`}
            onClick={() => setActiveTab('admin')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            Admin
          </button>
        </nav>
      </header>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main className="app-main">
        {activeTab === 'chat' ? <ChatPage /> : <AdminPage />}
      </main>
    </div>
  )
}
