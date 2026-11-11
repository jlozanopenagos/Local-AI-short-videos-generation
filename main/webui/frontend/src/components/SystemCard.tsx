import React, { useState, useEffect, useRef } from 'react'
import { Play, Square, RotateCw, Cpu, Sparkles, ChevronDown } from 'lucide-react'
import type { SystemStatus } from '../types'
import { controlService } from '../api'

interface SystemCardProps {
  system: SystemStatus | null
  onRefresh: () => void
}

export const SystemCard: React.FC<SystemCardProps> = ({ system, onRefresh }) => {
  const [busyService, setBusyService] = useState<string | null>(null)
  const [openPopover, setOpenPopover] = useState<boolean>(false)
  const stripRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!openPopover) return
    const handleClickOutside = (e: MouseEvent) => {
      if (stripRef.current && !stripRef.current.contains(e.target as Node)) {
        setOpenPopover(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [openPopover])

  const handleAction = async (
    service: 'comfyui' | 'llm',
    action: 'start' | 'stop' | 'restart',
    e?: React.MouseEvent
  ) => {
    if (e) e.stopPropagation()
    setBusyService(`${service}-${action}`)
    try {
      await controlService(service, action)
      setTimeout(onRefresh, 900)
    } catch (err) {
      alert(`Service action failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setBusyService(null)
    }
  }

  const comfy = system?.comfyui || (system as any)?.comfy
  const llm = system?.llm

  const comfyOnline = comfy?.status === 'online'
  const llmOnline = llm?.status === 'online'

  const vramUsed = comfy?.vram_usage_gb || 0
  const vramTotal = comfy?.vram_total_gb || 6.0
  const vramPct = Math.min(100, Math.round((vramUsed / (vramTotal || 1)) * 100))

  return (
    <div className="telemetry-strip" ref={stripRef} aria-label="Local engine telemetry">
      {/* ComfyUI Compact Chip */}
      <div
        className={`telemetry-chip ${openPopover ? 'active' : ''}`}
        onClick={() => setOpenPopover((prev) => !prev)}
        title="Click to inspect ComfyUI and Gemma server details"
      >
        <span className={`status-dot ${comfyOnline ? 'online' : 'offline'}`} />
        <span>ComfyUI</span>
        <span className="telemetry-chip-meta">
          {comfyOnline ? `${vramUsed.toFixed(1)}/${vramTotal.toFixed(0)} GB` : 'offline'}
        </span>
        <button
          className={`btn btn-sm ${comfyOnline ? 'btn-danger' : 'btn-success'}`}
          style={{ padding: '2px 5px', minHeight: '20px' }}
          disabled={busyService !== null}
          onClick={(e) => handleAction('comfyui', comfyOnline ? 'stop' : 'start', e)}
          title={comfyOnline ? 'Stop ComfyUI' : 'Start ComfyUI'}
        >
          {comfyOnline ? <Square size={10} /> : <Play size={10} />}
        </button>
      </div>

      {/* Gemma LLM Compact Chip */}
      <div
        className={`telemetry-chip ${openPopover ? 'active' : ''}`}
        onClick={() => setOpenPopover((prev) => !prev)}
        title="Click to inspect ComfyUI and Gemma server details"
      >
        <span className={`status-dot ${llmOnline ? 'online' : 'offline'}`} />
        <span>Gemma</span>
        <span className="telemetry-chip-meta">
          {llmOnline ? `:${llm?.port || 8080}` : 'on-demand'}
        </span>
        <button
          className={`btn btn-sm ${llmOnline ? 'btn-danger' : 'btn-success'}`}
          style={{ padding: '2px 5px', minHeight: '20px' }}
          disabled={busyService !== null}
          onClick={(e) => handleAction('llm', llmOnline ? 'stop' : 'start', e)}
          title={llmOnline ? 'Stop Gemma server' : 'Start Gemma server'}
        >
          {llmOnline ? <Square size={10} /> : <Play size={10} />}
        </button>
        <ChevronDown size={13} className="icon-muted" />
      </div>

      {/* Expandable Subtle Details Popover */}
      {openPopover && (
        <div className="telemetry-popover" role="dialog" aria-label="Server telemetry details">
          {/* ComfyUI Details */}
          <div className="telemetry-popover-card">
            <div className="service-header" style={{ marginBottom: '4px' }}>
              <div className="service-name" style={{ fontSize: '13.5px' }}>
                <Cpu size={15} className="icon-accent" />
                <span>ComfyUI diffusion engine</span>
              </div>
              <span className="telemetry-chip-meta">
                {comfyOnline ? 'online' : 'offline'}
              </span>
            </div>

            <div className="service-meta" style={{ marginBottom: '6px', fontSize: '12px' }}>
              <div className="meta-row">
                <span>Port / PID:</span>
                <span>{comfy?.port || 8188} / {comfy?.pid ?? '—'}</span>
              </div>
              <div className="meta-row">
                <span>Active GPU:</span>
                <span>{comfy?.active_gpu || 'Detecting...'}</span>
              </div>
              <div className="meta-row">
                <span>VRAM usage:</span>
                <span>{vramUsed.toFixed(2)} / {vramTotal.toFixed(1)} GB ({vramPct}%)</span>
              </div>
              <div className="vram-bar">
                <div
                  className="vram-fill"
                  style={{
                    width: `${vramPct}%`,
                    backgroundColor:
                      vramPct > 85
                        ? 'var(--danger)'
                        : vramPct > 65
                        ? 'var(--warning)'
                        : 'var(--accent)',
                  }}
                />
              </div>
              <div className="meta-row" style={{ marginTop: '4px' }}>
                <span>Queue:</span>
                <span>{comfy?.queue_running ?? 0} running, {comfy?.queue_pending ?? 0} pending</span>
              </div>
            </div>

            <div className="btn-group">
              {comfyOnline ? (
                <>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={busyService !== null}
                    onClick={(e) => handleAction('comfyui', 'stop', e)}
                  >
                    <Square size={12} />
                    <span>Stop</span>
                  </button>
                  <button
                    className="btn btn-outline btn-sm"
                    disabled={busyService !== null}
                    onClick={(e) => handleAction('comfyui', 'restart', e)}
                  >
                    <RotateCw size={12} />
                    <span>Restart</span>
                  </button>
                </>
              ) : (
                <button
                  className="btn btn-success btn-sm"
                  disabled={busyService !== null}
                  onClick={(e) => handleAction('comfyui', 'start', e)}
                >
                  <Play size={12} />
                  <span>Start ComfyUI</span>
                </button>
              )}
            </div>
          </div>

          {/* Gemma LLM Details */}
          <div className="telemetry-popover-card">
            <div className="service-header" style={{ marginBottom: '4px' }}>
              <div className="service-name" style={{ fontSize: '13.5px' }}>
                <Sparkles size={15} className="icon-sand" />
                <span>Gemma server (llama.cpp)</span>
              </div>
              <span className="telemetry-chip-meta">
                {llmOnline ? 'online' : 'offline'}
              </span>
            </div>

            <div className="service-meta" style={{ marginBottom: '6px', fontSize: '12px' }}>
              <div className="meta-row">
                <span>Port / PID:</span>
                <span>{llm?.port || 8080} / {llm?.pid ?? '—'}</span>
              </div>
              <div className="meta-row">
                <span>Model:</span>
                <span>{llm?.model || 'Gemma-4-E2B'}</span>
              </div>
              <div className="meta-row">
                <span>VRAM policy:</span>
                <span className="icon-success">Auto on-demand</span>
              </div>
              <div className="meta-row">
                <span>Role:</span>
                <span>Scripts & scene prompts</span>
              </div>
            </div>

            <div className="btn-group" style={{ marginTop: 'auto' }}>
              {llmOnline ? (
                <>
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={busyService !== null}
                    onClick={(e) => handleAction('llm', 'stop', e)}
                  >
                    <Square size={12} />
                    <span>Stop</span>
                  </button>
                  <button
                    className="btn btn-outline btn-sm"
                    disabled={busyService !== null}
                    onClick={(e) => handleAction('llm', 'restart', e)}
                  >
                    <RotateCw size={12} />
                    <span>Restart</span>
                  </button>
                </>
              ) : (
                <button
                  className="btn btn-success btn-sm"
                  disabled={busyService !== null}
                  onClick={(e) => handleAction('llm', 'start', e)}
                >
                  <Play size={12} />
                  <span>Start Gemma server</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

