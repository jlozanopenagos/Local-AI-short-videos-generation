import { useState, useEffect, useCallback } from 'react'
import { Navbar } from './components/Navbar'
import { HomeView } from './components/HomeView'
import { ScriptList } from './components/ScriptList'
import { ScriptDetailModal } from './components/ScriptDetailModal'
import { JobQueueView } from './components/JobQueueView'
import { GoogleSheetsSyncView } from './components/GoogleSheetsSyncView'
import { MassAssetsCreationView } from './components/MassAssetsCreationView'
import type { SystemStatus, Job } from './types'
import { fetchSystemStatus, fetchJobs } from './api'

type ActiveTab = 'home' | 'dashboard' | 'jobs' | 'sheets' | 'mass-creation'

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('home')
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('shorts_studio_theme')
    return (saved === 'light' || saved === 'dark') ? saved : 'dark'
  })
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedScriptId, setSelectedScriptId] = useState<string | null>(null)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  // Sync theme attribute to documentElement
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('shorts_studio_theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const loadSystem = useCallback(async () => {
    try {
      const data = await fetchSystemStatus()
      setSystem(data)
    } catch {
      // Backend temporarily offline / starting
    }
  }, [])

  const loadJobs = useCallback(async () => {
    try {
      const data = await fetchJobs()
      setJobs(data)
    } catch {
      // Backend error
    }
  }, [])

  const hasActiveJob = jobs.some((j) => j.status === 'running' || j.status === 'queued')

  // Initial load
  useEffect(() => {
    loadSystem()
    loadJobs()
  }, [loadSystem, loadJobs])

  // Adaptive status polling:
  // - Active job running/queued: poll system & jobs every 4s
  // - Idle (no active jobs): poll system status every 30s (skipping when tab is hidden), no redundant /api/jobs spam
  useEffect(() => {
    const intervalMs = hasActiveJob ? 4000 : 30000
    const timer = setInterval(() => {
      if (document.hidden && !hasActiveJob) return
      loadSystem()
      if (hasActiveJob || activeTab === 'jobs') {
        loadJobs()
      }
    }, intervalMs)
    return () => clearInterval(timer)
  }, [loadSystem, loadJobs, hasActiveJob, activeTab])

  // Refresh once when tab regains focus
  useEffect(() => {
    const onVisibilityChange = () => {
      if (!document.hidden) {
        loadSystem()
        loadJobs()
      }
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
  }, [loadSystem, loadJobs])

  // Update document title for local SEO and clarity
  useEffect(() => {
    if (selectedScriptId) {
      document.title = `Shorts studio — ${selectedScriptId}`
      return
    }
    const tabTitles: Record<ActiveTab, string> = {
      home: 'Shorts studio — Home',
      dashboard: 'Shorts studio — Script catalog',
      jobs: 'Shorts studio — Queue & console',
      sheets: 'Shorts studio — Google Sheets sync',
      'mass-creation': 'Shorts studio — Mass asset creation',
    }
    document.title = tabTitles[activeTab] || 'Shorts studio — AI video pipeline'
  }, [activeTab, selectedScriptId])

  const handleJobStarted = (jobId: string) => {
    setSelectedJobId(jobId)
    setActiveTab('jobs')
    loadJobs()
  }

  const handleCancelJob = (jobId: string) => {
    setJobs((prev) =>
      prev.map((j) => (j.job_id === jobId ? { ...j, status: 'cancelled' } : j))
    )
  }

  return (
    <div className="app-container">
      <Navbar
        system={system}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefreshSystem={loadSystem}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main className="main-content" aria-label="Main workspace">
        {activeTab === 'home' && (
          <div>
            <HomeView
              system={system}
              onNavigate={(tab) => setActiveTab(tab)}
              onSelectScript={(id) => setSelectedScriptId(id)}
            />
          </div>
        )}

        {activeTab === 'dashboard' && (
          <div>
            <ScriptList
              onSelectScript={(id) => setSelectedScriptId(id)}
              onJobStarted={handleJobStarted}
            />
          </div>
        )}

        {activeTab === 'jobs' && (
          <div>
            <JobQueueView
              jobs={jobs}
              selectedJobId={selectedJobId}
              onSelectJob={(id) => setSelectedJobId(id)}
              onRefresh={loadJobs}
              onCancelJob={handleCancelJob}
            />
          </div>
        )}

        {activeTab === 'sheets' && (
          <div>
            <GoogleSheetsSyncView
              onSelectScript={(id) => setSelectedScriptId(id)}
            />
          </div>
        )}

        {activeTab === 'mass-creation' && (
          <div>
            <MassAssetsCreationView
              system={system}
              onJobStarted={handleJobStarted}
              onSelectScript={(id) => setSelectedScriptId(id)}
            />
          </div>
        )}

        {/* Script Details Modal */}
        {selectedScriptId && (
          <ScriptDetailModal
            scriptId={selectedScriptId}
            onClose={() => {
              setSelectedScriptId(null)
            }}
            onJobStarted={handleJobStarted}
          />
        )}
      </main>
    </div>
  )
}

export default App
