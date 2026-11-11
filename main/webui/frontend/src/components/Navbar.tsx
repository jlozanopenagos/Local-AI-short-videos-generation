import React from 'react'
import { Home, Cpu, Terminal, Video, FileSpreadsheet, Layers, Sun, Moon } from 'lucide-react'
import type { SystemStatus } from '../types'
import { SystemCard } from './SystemCard'

interface NavbarProps {
  system: SystemStatus | null
  activeTab: 'home' | 'dashboard' | 'jobs' | 'sheets' | 'mass-creation'
  setActiveTab: (tab: 'home' | 'dashboard' | 'jobs' | 'sheets' | 'mass-creation') => void
  onRefreshSystem: () => void
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  system,
  activeTab,
  setActiveTab,
  onRefreshSystem,
  theme,
  onToggleTheme,
}) => {
  return (
    <header className="header">
      <div
        className="brand"
        onClick={() => setActiveTab('home')}
        style={{ cursor: 'pointer', userSelect: 'none' }}
        title="Go to homepage"
      >
        <Video size={22} className="icon-accent" />
        <span>Shorts studio</span>
        <span className="brand-badge">local</span>
      </div>

      <nav className="nav-links" aria-label="Primary navigation">
        <button
          className={`nav-btn ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')}
        >
          <Home size={16} />
          <span>Home</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <Cpu size={16} />
          <span>Script catalog</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Terminal size={16} />
          <span>Queue & console</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'sheets' ? 'active' : ''}`}
          onClick={() => setActiveTab('sheets')}
        >
          <FileSpreadsheet size={16} />
          <span>Google Sheets sync</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'mass-creation' ? 'active' : ''}`}
          onClick={() => setActiveTab('mass-creation')}
        >
          <Layers size={16} />
          <span>Mass asset creation</span>
        </button>
      </nav>

      <div className="header-status">
        {/* Dual Theme Switcher */}
        <button
          className="theme-toggle-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to Light theme' : 'Switch to Dark theme'}
          aria-label="Toggle visual theme"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Engine Telemetry */}
        <SystemCard system={system} onRefresh={onRefreshSystem} />
      </div>
    </header>
  )
}


