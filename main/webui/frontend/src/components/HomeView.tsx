import React, { useState, useEffect } from 'react'
import {
  Sparkles,
  ArrowRight,
  Cpu,
  Layers,
  FileSpreadsheet,
  Terminal,
  CheckCircle2,
  Clock,
  Film,
  Layers as LayersIcon
} from 'lucide-react'
import type { SystemStatus, ScriptFacets, ScriptSummary } from '../types'
import { fetchScriptCatalog, fetchFacets } from '../api'

interface HomeViewProps {
  system: SystemStatus | null
  onNavigate: (tab: 'dashboard' | 'jobs' | 'sheets' | 'mass-creation') => void
  onSelectScript: (scriptId: string) => void
}

export const HomeView: React.FC<HomeViewProps> = ({
  system,
  onNavigate,
  onSelectScript,
}) => {
  const [facets, setFacets] = useState<ScriptFacets | null>(null)
  const [readyScripts, setReadyScripts] = useState<ScriptSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    const loadHomeData = async () => {
      setLoading(true)
      try {
        const [facetsData, readyCatalog] = await Promise.all([
          fetchFacets().catch(() => null),
          fetchScriptCatalog({ pageSize: 6, stageFilter: 'ready_for_assembly' }).catch(() => null),
        ])
        if (!isMounted) return
        if (facetsData) setFacets(facetsData)
        if (readyCatalog && Array.isArray((readyCatalog as any).items)) {
          setReadyScripts((readyCatalog as any).items)
        }
      } catch (err) {
        console.error('Failed to load home metrics:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    loadHomeData()
    return () => {
      isMounted = false
    }
  }, [])

  const comfyOnline = system?.comfyui?.status === 'online' || (system as any)?.comfy?.status === 'online'
  const llmOnline = system?.llm?.status === 'online'

  const totalScripts = facets?.total ?? 1225
  const completedCount = facets?.stage_counts?.complete ?? 0
  const readyAssemblyCount = facets?.stage_counts?.ready_for_assembly ?? 0

  return (
    <section className="home-container" aria-label="Shorts studio homepage">
      {/* Hero Welcome Card */}
      <div className="home-hero-card">
        <div className="home-hero-badge">
          <Sparkles size={14} />
          <span>Local AI video production workspace</span>
        </div>
        <h1 className="home-hero-title">
          Shorts studio — automated video pipeline
        </h1>
        <p className="home-hero-desc">
          High-efficiency local orchestration for multilingual educational shorts. Generate spoken dialogues,
          synthesize multi-character voices, diffuse 2D scene artwork in ComfyUI, and assemble vertical videos in bulk.
        </p>

        <div className="home-hero-actions">
          <button
            className="btn btn-primary"
            onClick={() => onNavigate('dashboard')}
          >
            <span>Explore script catalog</span>
            <ArrowRight size={15} />
          </button>
          <button
            className="btn btn-outline"
            onClick={() => onNavigate('mass-creation')}
          >
            <LayersIcon size={15} />
            <span>Mass asset creation</span>
          </button>
          <button
            className="btn btn-outline"
            onClick={() => onNavigate('sheets')}
          >
            <FileSpreadsheet size={15} />
            <span>Google Sheets sync</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="home-kpi-grid">
        <div className="home-kpi-card">
          <div className="home-kpi-icon" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
            <Cpu size={22} />
          </div>
          <div className="home-kpi-content">
            <span className="home-kpi-value">{totalScripts.toLocaleString()}</span>
            <span className="home-kpi-label">Total scripts indexed</span>
          </div>
        </div>

        <div className="home-kpi-card">
          <div className="home-kpi-icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
            <CheckCircle2 size={22} />
          </div>
          <div className="home-kpi-content">
            <span className="home-kpi-value">{completedCount.toLocaleString()}</span>
            <span className="home-kpi-label">Completed short videos</span>
          </div>
        </div>

        <div className="home-kpi-card">
          <div className="home-kpi-icon" style={{ background: 'var(--sand-subtle)', color: 'var(--sand)' }}>
            <Clock size={22} />
          </div>
          <div className="home-kpi-content">
            <span className="home-kpi-value">{readyAssemblyCount.toLocaleString()}</span>
            <span className="home-kpi-label">Ready for video assembly</span>
          </div>
        </div>

        <div className="home-kpi-card">
          <div
            className="home-kpi-icon"
            style={{
              background: comfyOnline && llmOnline ? 'var(--success-bg)' : 'var(--warning-bg)',
              color: comfyOnline && llmOnline ? 'var(--success)' : 'var(--warning)',
            }}
          >
            <Film size={22} />
          </div>
          <div className="home-kpi-content">
            <span className="home-kpi-value" style={{ fontSize: '18px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className={`status-dot ${comfyOnline ? 'online' : 'offline'}`} />
              <span>{comfyOnline ? 'Online' : 'Offline'}</span>
            </span>
            <span className="home-kpi-label">
              ComfyUI {comfyOnline ? ':8188' : ''} • Gemma {llmOnline ? ':8080' : 'standby'}
            </span>
          </div>
        </div>
      </div>

      {/* Core Workflow Cards Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <h2 className="home-section-title">
          <span>Production workflows</span>
        </h2>

        <div className="home-workflow-grid">
          {/* Card 1: Script Catalog */}
          <div className="home-workflow-card" onClick={() => onNavigate('dashboard')}>
            <div className="home-workflow-top">
              <div className="home-workflow-icon-wrap" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                <Cpu size={22} />
              </div>
              <h3 className="home-workflow-heading">Script catalog</h3>
              <p className="home-workflow-desc">
                Browse, search, and inspect 1,225+ scripts across English, Spanish, French, and Italian. Edit dialogues, chalkboard exercises, and scene prompts.
              </p>
            </div>
            <span className="home-workflow-arrow">
              <span>Open catalog</span>
              <ArrowRight size={14} />
            </span>
          </div>

          {/* Card 2: Mass Asset Creation */}
          <div className="home-workflow-card" onClick={() => onNavigate('mass-creation')}>
            <div className="home-workflow-top">
              <div className="home-workflow-icon-wrap" style={{ background: 'var(--sand-subtle)', color: 'var(--sand)' }}>
                <Layers size={22} />
              </div>
              <h3 className="home-workflow-heading">Mass asset creation</h3>
              <p className="home-workflow-desc">
                Batch render scene illustrations, Kokoro voice narration, title thumbnails, or game chalkboard typography across targeted script IDs.
              </p>
            </div>
            <span className="home-workflow-arrow">
              <span>Start mass run</span>
              <ArrowRight size={14} />
            </span>
          </div>

          {/* Card 3: Google Sheets Sync */}
          <div className="home-workflow-card" onClick={() => onNavigate('sheets')}>
            <div className="home-workflow-top">
              <div className="home-workflow-icon-wrap" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
                <FileSpreadsheet size={22} />
              </div>
              <h3 className="home-workflow-heading">Google Sheets sync</h3>
              <p className="home-workflow-desc">
                Fetch script edits directly from remote Google Sheets, purge stale CSV files, review side-by-side diffs, and automatically update local state JSONs.
              </p>
            </div>
            <span className="home-workflow-arrow">
              <span>Synchronize sheets</span>
              <ArrowRight size={14} />
            </span>
          </div>

          {/* Card 4: Queue & Console */}
          <div className="home-workflow-card" onClick={() => onNavigate('jobs')}>
            <div className="home-workflow-top">
              <div className="home-workflow-icon-wrap" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                <Terminal size={22} />
              </div>
              <h3 className="home-workflow-heading">Queue & console</h3>
              <p className="home-workflow-desc">
                Monitor running worker processes, cancel active batch tasks, and stream real-time logging output from the pipeline execution engine.
              </p>
            </div>
            <span className="home-workflow-arrow">
              <span>View console</span>
              <ArrowRight size={14} />
            </span>
          </div>
        </div>
      </div>

      {/* Ready for Assembly Spotlight */}
      <div className="home-spotlight-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-main)' }}>
              Ready for assembly spotlight
            </h3>
            <p style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
              Scripts that have both voice and scene images completed, ready for final video compilation.
            </p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={() => onNavigate('dashboard')}>
            <span>View all in catalog</span>
            <ArrowRight size={13} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            Loading studio spotlight...
          </div>
        ) : readyScripts.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No scripts currently waiting for assembly. All assembled or awaiting audio/images.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="scripts-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Topic / title</th>
                  <th>Language / format</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {readyScripts.map((s) => (
                  <tr key={s.script_id} onClick={() => onSelectScript(s.script_id)}>
                    <td>
                      <strong className="icon-sand" style={{ fontFamily: 'var(--font-mono)' }}>
                        {s.script_id}
                      </strong>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{s.title || s.topic}</div>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{s.language}</span> /{' '}
                      <span className="brand-badge badge-sand" style={{ fontSize: '10.5px' }}>
                        {s.type}
                      </span>
                    </td>
                    <td>
                      <span className="stage-badge stage-done">
                        Ready for assembly
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectScript(s.script_id)
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}
