import { useState, useEffect, useCallback } from 'react'
import { Navbar } from './components/Navbar'
import { SystemCard } from './components/SystemCard'
import { ScriptList } from './components/ScriptList'
import { ScriptDetailModal } from './components/ScriptDetailModal'
import { JobQueueView } from './components/JobQueueView'
import { GoogleSheetsSyncView } from './components/GoogleSheetsSyncView'
import { MassAssetsCreationView } from './components/MassAssetsCreationView'
import type { SystemStatus, Job } from './types'
import { fetchSystemStatus, fetchJobs } from './api'

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'jobs' | 'sheets' | 'mass-creation'>('dashboard')
  const [system, setSystem] = useState<SystemStatus | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedScriptId, setSelectedScriptId] = useState<string | null>(null)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

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

  // Initial load
  useEffect(() => {
    loadSystem()
    loadJobs()
  }, [loadSystem, loadJobs])

  // Periodic status poll (every 4s)
  useEffect(() => {
    const timer = setInterval(() => {
      loadSystem()
      loadJobs()
    }, 4000)
    return () => clearInterval(timer)
  }, [loadSystem, loadJobs])

  const handleJobStarted = (jobId: string) => {
    setSelectedJobId(jobId)
    setActiveTab('jobs')
    loadJobs()
  }

  return (
    <div className="app-container">
      <Navbar
        system={system}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefreshSystem={loadSystem}
      />

      <main className="main-content">
        {/* Top Service Telemetry on all views */}
        <SystemCard system={system} onRefresh={loadSystem} />

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
