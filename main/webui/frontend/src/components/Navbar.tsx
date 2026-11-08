import React from 'react'
import { Play, Square, Cpu, Terminal, Video } from 'lucide-react'
import type { SystemStatus } from '../types'
import { controlService } from '../api'

interface NavbarProps {
  system: SystemStatus | null
  activeTab: 'dashboard' | 'jobs'
  setActiveTab: (tab: 'dashboard' | 'jobs') => void
  onRefreshSystem: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  system,
  activeTab,
  setActiveTab,
  onRefreshSystem,
}) => {
  const [loadingAction, setLoadingAction] = React.useState<string | null>(null)

  const handleToggleService = async (service: 'comfyui' | 'llm', currentStatus: string) => {
    const action = currentStatus === 'online' ? 'stop' : 'start'
    setLoadingAction(`${service}-${action}`)
    try {
      await controlService(service, action)
      setTimeout(onRefreshSystem, 800)
    } catch (err) {
      alert(`Error toggling ${service}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoadingAction(null)
    }
  }

  const comfyOnline = (system?.comfyui?.status === 'online') || ((system as any)?.comfy?.status === 'online')
  const llmOnline = system?.llm?.status === 'online'

  return (
    <header className="header">
      <div className="brand">
        <Video size={22} className="text-blue-500" />
        <span>SHORTS STUDIO</span>
        <span className="brand-badge">WEBUI</span>
      </div>

      <nav className="nav-links">
        <button
          className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <Cpu size={16} />
          <span>Dashboard</span>
        </button>
        <button
          className={`nav-btn ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          <Terminal size={16} />
          <span>Queue & Console</span>
        </button>
      </nav>

      <div className="header-status">
        {/* ComfyUI Quick Control */}
        <div className="status-pill">
          <div className={`status-dot ${comfyOnline ? 'online' : 'offline'}`} />
          <span>ComfyUI: {comfyOnline ? '8188' : 'OFF'}</span>
          <button
            className={`btn btn-sm ${comfyOnline ? 'btn-danger' : 'btn-success'}`}
            disabled={loadingAction === 'comfyui-start' || loadingAction === 'comfyui-stop'}
            onClick={() => handleToggleService('comfyui', system?.comfyui.status || 'offline')}
            title={comfyOnline ? 'Stop ComfyUI' : 'Start ComfyUI'}
          >
            {comfyOnline ? <Square size={12} /> : <Play size={12} />}
          </button>
        </div>

        {/* LLM Quick Control */}
        <div className="status-pill">
          <div className={`status-dot ${llmOnline ? 'online' : 'offline'}`} />
          <span>LLM: {llmOnline ? '8080' : 'OFF'}</span>
          <button
            className={`btn btn-sm ${llmOnline ? 'btn-danger' : 'btn-success'}`}
            disabled={loadingAction === 'llm-start' || loadingAction === 'llm-stop'}
            onClick={() => handleToggleService('llm', system?.llm.status || 'offline')}
            title={llmOnline ? 'Stop LLM' : 'Start LLM'}
          >
            {llmOnline ? <Square size={12} /> : <Play size={12} />}
          </button>
        </div>
      </div>
    </header>
  )
}

