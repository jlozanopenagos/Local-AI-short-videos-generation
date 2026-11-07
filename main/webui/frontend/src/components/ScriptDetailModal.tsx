import React from 'react'
import { X, Image, Mic, Film, Sparkles } from 'lucide-react'
import type { ScriptDetail, JobStage } from '../types'
import { fetchScriptDetail, getMediaUrl, createJob } from '../api'

interface ScriptDetailModalProps {
  scriptId: string
  onClose: () => void
  onJobStarted: (jobId: string) => void
}

export const ScriptDetailModal: React.FC<ScriptDetailModalProps> = ({
  scriptId,
  onClose,
  onJobStarted,
}) => {
  const [detail, setDetail] = React.useState<ScriptDetail | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [activeTab, setActiveTab] = React.useState<'overview' | 'scenes' | 'assets'>('overview')
  const [triggeringStage, setTriggeringStage] = React.useState<string | null>(null)

  const loadData = React.useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchScriptDetail(scriptId)
      setDetail(data)
    } catch (err) {
      alert(`Failed to load script ${scriptId}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, [scriptId])

  React.useEffect(() => {
    loadData()
  }, [loadData])

  const handleRunStage = async (stage: JobStage) => {
    setTriggeringStage(stage)
    try {
      const job = await createJob(stage, [scriptId])
      onJobStarted(job.job_id)
      onClose()
    } catch (err) {
      alert(`Could not start ${stage}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setTriggeringStage(null)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        {loading || !detail ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            Loading script details for {scriptId}...
          </div>
        ) : (
          <div>
            {/* Header info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700 }}>
                <span style={{ color: 'var(--accent)' }}>[{detail.script_id}]</span> {detail.topic}
              </h2>
              <span className="brand-badge" style={{ textTransform: 'uppercase' }}>
                {detail.language} / {detail.type}
              </span>
            </div>

            {/* Quick Actions Bar */}
            <div
              style={{
                display: 'flex',
                gap: '8px',
                flexWrap: 'wrap',
                background: 'var(--bg-input)',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '20px',
                border: '1px solid var(--border)',
              }}
            >
              <span style={{ fontSize: '13px', fontWeight: 600, alignSelf: 'center', marginRight: '6px' }}>
                Run Pipeline:
              </span>
              <button
                className="btn btn-outline btn-sm"
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('voice')}
              >
                <Mic size={14} />
                <span>Voice (B)</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('images')}
              >
                <Image size={14} />
                <span>Images (C)</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('thumbnails')}
              >
                <Sparkles size={14} />
                <span>Thumbnail (F)</span>
              </button>
              <button
                className="btn btn-primary btn-sm"
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('assembly')}
              >
                <Film size={14} />
                <span>Assemble Video (G)</span>
              </button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
              <button
                className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Overview & Character
              </button>
              <button
                className={`nav-btn ${activeTab === 'scenes' ? 'active' : ''}`}
                onClick={() => setActiveTab('scenes')}
              >
                Scenes & Script ({detail.scenes?.length || 0})
              </button>
              <button
                className={`nav-btn ${activeTab === 'assets' ? 'active' : ''}`}
                onClick={() => setActiveTab('assets')}
              >
                Generated Assets ({detail.assets?.images?.length || 0} images)
              </button>
            </div>

            {/* Tab: Overview */}
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px' }}>
                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Story Scenario:</strong>
                  <p style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '10px', borderRadius: '6px' }}>
                    {detail.story_scenario || 'Not configured yet.'}
                  </p>
                </div>
                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Base Setting:</strong>
                  <p style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '10px', borderRadius: '6px' }}>
                    {detail.base_setting || 'Not configured yet.'}
                  </p>
                </div>
                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Character:</strong>
                  <div style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '10px', borderRadius: '6px' }}>
                    <div><strong>Gender:</strong> {detail.character?.gender || 'Male (default)'}</div>
                    <div><strong>Details:</strong> {detail.character?.description || 'Standard teen style'}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Scenes */}
            {activeTab === 'scenes' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {(detail.scenes || []).map((sc, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border)',
                      borderRadius: '8px',
                      padding: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span className="brand-badge">{sc.scene_type}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Scene {idx + 1}</span>
                    </div>
                    <div style={{ fontSize: '14px', marginBottom: '8px' }}>
                      "{sc.voice_line}"
                    </div>
                    {sc.prompt && (
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: '6px' }}>
                        Prompt: {sc.prompt}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Tab: Assets */}
            {activeTab === 'assets' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Voice audio preview */}
                {detail.assets.audio ? (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Voice Audio</h4>
                    <audio controls style={{ width: '100%' }} src={getMediaUrl(detail.assets.audio)} />
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No voice generated yet.</div>
                )}

                {/* Final video preview */}
                {detail.assets.video && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Final Short Video</h4>
                    <video controls style={{ maxWidth: '300px', borderRadius: '8px', border: '1px solid var(--border)' }} src={getMediaUrl(detail.assets.video)} />
                  </div>
                )}

                {/* Thumbnail */}
                {detail.assets.thumbnail && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Chalkboard Thumbnail</h4>
                    <img
                      src={getMediaUrl(detail.assets.thumbnail)}
                      alt="Thumbnail"
                      style={{ maxWidth: '240px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                )}

                {/* Scene Images */}
                <div>
                  <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>
                    Scene Images ({detail.assets.images.length})
                  </h4>
                  {detail.assets.images.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No scene images generated yet.</div>
                  ) : (
                    <div className="gallery-grid">
                      {detail.assets.images.map((imgPath, idx) => (
                        <div key={idx} className="gallery-item">
                          <img src={getMediaUrl(imgPath)} alt={`Scene ${idx + 1}`} loading="lazy" />
                          <div className="gallery-label">Scene {idx + 1}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
