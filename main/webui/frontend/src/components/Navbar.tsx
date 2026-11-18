import React from 'react'
import { Home, Cpu, LayoutGrid, Terminal, Video, FileSpreadsheet, Layers, Sun, Moon } from 'lucide-react'
import type { SystemStatus, ActiveTab } from '../types'
import { SystemCard } from './SystemCard'

interface NavbarProps {
  system: SystemStatus | null
  activeTab: ActiveTab
  setActiveTab: (tab: ActiveTab) => void
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
        title="go to homepage"
      >
        <Video size={22} className="icon-accent" />
        <span>Shorts studio</span>
        <span className="brand-badge">local</span>
      </div>

      <nav className="nav-links" aria-label="primary navigation">
        <button
          className={`nav-btn ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')}
        >
          <Home size={15} />
          <span>home</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <Cpu size={15} />
          <span>script catalog</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Terminal size={15} />
          <span>queue</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'mass-creation' ? 'active' : ''}`}
          onClick={() => setActiveTab('mass-creation')}
        >
          <Layers size={15} />
          <span>mass creation</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'sheets' ? 'active' : ''}`}
          onClick={() => setActiveTab('sheets')}
        >
          <FileSpreadsheet size={15} />
          <span>sheets sync</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'bingo' ? 'active' : ''}`}
          onClick={() => setActiveTab('bingo')}
          title="visual asset pipeline tracker across all IDs"
        >
          <LayoutGrid size={15} />
          <span>bingo matrix</span>
        </button>
      </nav>

      <div className="header-status">
        {/* Dual Theme Switcher */}
        <button
          className="theme-toggle-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'switch to light theme' : 'switch to dark theme'}
          aria-label="toggle visual theme"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Engine Telemetry */}
        <SystemCard system={system} onRefresh={onRefreshSystem} />
      </div>
    </header>
  )
}


