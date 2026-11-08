import React from 'react'
import { Play, Square, RotateCw, Cpu, Sparkles } from 'lucide-react'
import type { SystemStatus } from '../types'
import { controlService } from '../api'

interface SystemCardProps {
  system: SystemStatus | null
  onRefresh: () => void
}

export const SystemCard: React.FC<SystemCardProps> = ({ system, onRefresh }) => {
  const [busyService, setBusyService] = React.useState<string | null>(null)

  const handleAction = async (service: 'comfyui' | 'llm', action: 'start' | 'stop' | 'restart') => {
    setBusyService(`${service}-${action}`)
    try {
      await controlService(service, action)
      setTimeout(onRefresh, 1000)
    } catch (err) {
      alert(`Service action failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setBusyService(null)
    }
  }

  const comfy = system?.comfyui || (system as any)?.comfy
  const llm = system?.llm

  const vramUsed = comfy?.vram_usage_gb || 0
  const vramTotal = comfy?.vram_total_gb || 6.0
  const vramPct = Math.min(100, Math.round((vramUsed / (vramTotal || 1)) * 100))

  return (
    <div className="service-grid">
      {/* ComfyUI Card */}
      <div className="service-card">
        <div className="service-header">
          <div className="service-name">
            <Cpu size={18} />
            <span>ComfyUI Diffusion Engine</span>
          </div>
          <div className={`status-pill`}>
            <div className={`status-dot ${comfy?.status === 'online' ? 'online' : 'offline'}`} />
            <span>{comfy?.status ? comfy.status.toUpperCase() : 'OFFLINE'}</span>
          </div>
        </div>

        <div className="service-meta">
          <div className="meta-row">
            <span>Port / PID:</span>
            <span>{comfy?.port || 8188} / {comfy?.pid ?? '—'}</span>
          </div>
          <div className="meta-row">
            <span>Active GPU:</span>
            <span>{comfy?.active_gpu || 'Detecting...'}</span>
          </div>
          <div className="meta-row">
            <span>VRAM Allocation:</span>
            <span>{vramUsed.toFixed(2)} GB / {vramTotal.toFixed(1)} GB ({vramPct}%)</span>
          </div>
          <div className="vram-bar">
            <div
              className="vram-fill"
              style={{
                width: `${vramPct}%`,
                backgroundColor: vramPct > 85 ? 'var(--danger)' : vramPct > 65 ? 'var(--warning)' : 'var(--accent)',
              }}
            />
          </div>
          <div className="meta-row" style={{ marginTop: '6px' }}>
            <span>Queue:</span>
            <span>{comfy?.queue_running ?? 0} running, {comfy?.queue_pending ?? 0} pending</span>
          </div>
        </div>

        <div className="btn-group">
          {comfy?.status === 'online' ? (
            <>
              <button
                className="btn btn-danger btn-sm"
                disabled={busyService !== null}
                onClick={() => handleAction('comfyui', 'stop')}
              >
                <Square size={13} />
                <span>Stop</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                disabled={busyService !== null}
                onClick={() => handleAction('comfyui', 'restart')}
              >
                <RotateCw size={13} />
                <span>Restart</span>
              </button>
            </>
          ) : (
            <button
              className="btn btn-success btn-sm"
              disabled={busyService !== null}
              onClick={() => handleAction('comfyui', 'start')}
            >
              <Play size={13} />
              <span>Start ComfyUI</span>
            </button>
          )}
        </div>
      </div>

      {/* LLM (llama.cpp) Card */}
      <div className="service-card">
        <div className="service-header">
          <div className="service-name">
            <Sparkles size={18} />
            <span>llama.cpp Supervisor (Gemma)</span>
          </div>
          <div className="status-pill">
            <div className={`status-dot ${llm?.status === 'online' ? 'online' : 'offline'}`} />
            <span>{llm?.status ? llm.status.toUpperCase() : 'OFFLINE'}</span>
          </div>
        </div>

        <div className="service-meta">
          <div className="meta-row">
            <span>Port / PID:</span>
            <span>{llm?.port || 8080} / {llm?.pid ?? '—'}</span>
          </div>
          <div className="meta-row">
            <span>Model:</span>
            <span>{llm?.model || 'Gemma-4-E2B'}</span>
          </div>
          <div className="meta-row">
            <span>VRAM Policy:</span>
            <span style={{ color: 'var(--success)' }}>Auto On-Demand (Released for ComfyUI)</span>
          </div>
          <div className="meta-row">
            <span>Role:</span>
            <span>Prompt generation, Story Scenario & Setting expansion</span>
          </div>
        </div>

        <div className="btn-group">
          {llm?.status === 'online' ? (
            <>
              <button
                className="btn btn-danger btn-sm"
                disabled={busyService !== null}
                onClick={() => handleAction('llm', 'stop')}
              >
                <Square size={13} />
                <span>Stop</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                disabled={busyService !== null}
                onClick={() => handleAction('llm', 'restart')}
              >
                <RotateCw size={13} />
                <span>Restart</span>
              </button>
            </>
          ) : (
            <button
              className="btn btn-success btn-sm"
              disabled={busyService !== null}
              onClick={() => handleAction('llm', 'start')}
            >
              <Play size={13} />
              <span>Start LLM Server</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
