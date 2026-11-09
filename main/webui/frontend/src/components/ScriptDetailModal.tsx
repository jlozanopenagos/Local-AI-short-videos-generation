import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Image as ImageIcon,
  Mic,
  Film,
  Sparkles,
  Copy,
  Check,
  Save,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Code,
  Edit3
} from 'lucide-react'
import type { ScriptDetail, JobStage } from '../types'
import {
  fetchScriptDetail,
  getMediaUrl,
  createJob,
  updateScript,
  geminiAuditPrompt,
  fetchGeminiStatus,
  saveGeminiKey
} from '../api'

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
  const [detail, setDetail] = useState<ScriptDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'storyboard' | 'overview' | 'youtube' | 'media'>('storyboard')
  const [triggeringStage, setTriggeringStage] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Storyboard local state
  const [editGeneralPrompt, setEditGeneralPrompt] = useState('')
  const [savingGeneralPrompt, setSavingGeneralPrompt] = useState(false)
  const [auditingGemini, setAuditingGemini] = useState(false)
  const [showGeminiKeyModal, setShowGeminiKeyModal] = useState(false)
  const [geminiKeyInput, setGeminiKeyInput] = useState('')
  const [savingGeminiKey, setSavingGeminiKey] = useState(false)
  const [generalPromptStatus, setGeneralPromptStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [editScenePrompts, setEditScenePrompts] = useState<Record<string, string>>({})
  const [savingSceneType, setSavingSceneType] = useState<string | null>(null)

  // Script & Chalkboard editor local state
  const [chalkboardTitle, setChalkboardTitle] = useState('')
  const [chalkboardExercise, setChalkboardExercise] = useState('')
  const [scriptFields, setScriptFields] = useState<Record<string, string>>({})
  const [jsonMode, setJsonMode] = useState(false)
  const [rawJsonText, setRawJsonText] = useState('')
  const [savingScript, setSavingScript] = useState(false)
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const populateEditorState = (data: ScriptDetail) => {
    // 1. General & Scene prompts
    setEditGeneralPrompt(data.general_prompt || '')
    const scenePromptMap: Record<string, string> = {}
    if (data.scenes) {
      data.scenes.forEach((sc) => {
        scenePromptMap[sc.scene_type] = sc.prompt || ''
      })
    }
    setEditScenePrompts(scenePromptMap)

    // 2. Chalkboard
    const titleVal = data.chalkboard_title || data.target_expression || data.title || ''
    setChalkboardTitle(titleVal)
    setChalkboardExercise(data.chalkboard_exercise || '')

    // 3. Script structure
    let sDict: Record<string, any> = {}
    if (data.script_dict && Object.keys(data.script_dict).length > 0) {
      sDict = { ...data.script_dict }
    } else if (data.script_text) {
      try {
        const parsed = JSON.parse(data.script_text)
        if (typeof parsed === 'object' && parsed !== null) {
          sDict = parsed
        }
      } catch {
        sDict = { script_text: data.script_text }
      }
    }
    setScriptFields(sDict)
    setRawJsonText(JSON.stringify(sDict, null, 2))
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchScriptDetail(scriptId)
      setDetail(data)
      populateEditorState(data)
    } catch (err) {
      alert(`Failed to load script ${scriptId}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, [scriptId])

  useEffect(() => {
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

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  // --- Storyboard Actions ---
  const handleGeminiAudit = async () => {
    setGeneralPromptStatus(null)
    try {
      const status = await fetchGeminiStatus()
      if (!status.configured) {
        setShowGeminiKeyModal(true)
        return
      }
    } catch {
      // Continue to try audit directly
    }

    await executeAudit()
  }

  const executeAudit = async (apiKeyOverride?: string) => {
    setAuditingGemini(true)
    setGeneralPromptStatus(null)
    try {
      const updated = await geminiAuditPrompt(scriptId, editGeneralPrompt, apiKeyOverride)
      setDetail(updated)
      populateEditorState(updated)
      setGeneralPromptStatus({
        type: 'success',
        message: '✨ Audited by Gemini! New General Prompt saved and Image Generation set to PENDING. Click "Images (C)" in the header to render.',
      })
      setTimeout(() => {
        setGeneralPromptStatus(null)
      }, 8000)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('GEMINI_API_KEY is not configured')) {
        setShowGeminiKeyModal(true)
      } else {
        setGeneralPromptStatus({
          type: 'error',
          message: msg,
        })
      }
    } finally {
      setAuditingGemini(false)
    }
  }

  const handleSaveGeminiKeyAndAudit = async () => {
    if (!geminiKeyInput.trim()) return
    setSavingGeminiKey(true)
    try {
      await saveGeminiKey(geminiKeyInput.trim())
      setShowGeminiKeyModal(false)
      await executeAudit(geminiKeyInput.trim())
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err))
    } finally {
      setSavingGeminiKey(false)
    }
  }

  const handleSaveGeneralPrompt = async () => {
    setSavingGeneralPrompt(true)
    setGeneralPromptStatus(null)
    try {
      const isNewVersion = editGeneralPrompt.trim() !== (detail?.general_prompt || '').trim()
      const updated = await updateScript(scriptId, {
        general_prompt: editGeneralPrompt,
      })
      setDetail(updated)
      populateEditorState(updated)

      if (isNewVersion) {
        setGeneralPromptStatus({
          type: 'success',
          message: '✓ Saved! General prompt updated and Image Generation marked as PENDING. Click "Images (C)" in the header to re-generate scene prompts & images.',
        })
      } else {
        setGeneralPromptStatus({
          type: 'success',
          message: '✓ General prompt saved (no changes detected).',
        })
      }

      setTimeout(() => {
        setGeneralPromptStatus(null)
      }, 7000)
    } catch (err) {
      setGeneralPromptStatus({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setSavingGeneralPrompt(false)
    }
  }

  const handleSaveScenePrompt = async (sceneType: string) => {
    setSavingSceneType(sceneType)
    try {
      const updated = await updateScript(scriptId, {
        image_prompts: {
          [sceneType]: editScenePrompts[sceneType] || '',
        },
      })
      setDetail(updated)
      populateEditorState(updated)
    } catch (err) {
      alert(`Failed to save prompt for ${sceneType}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSavingSceneType(null)
    }
  }

  // --- Script & Chalkboard Actions ---
  const handleFieldChange = (key: string, value: string) => {
    const updated = { ...scriptFields, [key]: value }
    setScriptFields(updated)
    setRawJsonText(JSON.stringify(updated, null, 2))
  }

  const handleSaveScriptAndChalkboard = async () => {
    setSavingScript(true)
    setSaveStatus(null)
    try {
      let finalScriptDict: Record<string, any> = scriptFields
      let finalScriptText: string = rawJsonText

      if (jsonMode) {
        try {
          finalScriptDict = JSON.parse(rawJsonText)
          finalScriptText = rawJsonText
        } catch {
          setSaveStatus({
            type: 'error',
            message: 'Invalid JSON syntax. Please verify and correct your JSON before saving.',
          })
          setSavingScript(false)
          return
        }
      } else {
        finalScriptText = JSON.stringify(finalScriptDict, null, 2)
      }

      const updated = await updateScript(scriptId, {
        chalkboard_title: chalkboardTitle,
        target_expression: chalkboardTitle,
        chalkboard_exercise: chalkboardExercise,
        script_dict: finalScriptDict,
        script_text: finalScriptText,
      })

      setDetail(updated)
      populateEditorState(updated)
      setSaveStatus({
        type: 'success',
        message: '✓ Saved! Script and Chalkboard state updated on disk.',
      })

      setTimeout(() => {
        setSaveStatus(null)
      }, 4000)
    } catch (err) {
      setSaveStatus({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setSavingScript(false)
    }
  }

  const handleResetEditor = () => {
    if (detail) {
      populateEditorState(detail)
      setSaveStatus(null)
      setGeneralPromptStatus(null)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        {loading || !detail ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
            Loading script data for {scriptId}...
          </div>
        ) : (
          <div>
            {/* Header info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700 }}>
                <span style={{ color: 'var(--accent)' }}>[{detail.script_id}]</span> {detail.title || detail.topic}
              </h2>
              <span className="brand-badge" style={{ textTransform: 'uppercase' }}>
                {detail.language} / {detail.type}
              </span>
            </div>

            {/* Pipeline Stage Action Bar */}
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
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '13px', fontWeight: 600, marginRight: '4px' }}>
                Run Pipeline:
              </span>
              <button
                className={`btn btn-sm ${detail.stages.voice === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('voice')}
              >
                <Mic size={13} />
                <span>Voice (B) {detail.stages.voice === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.images === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('images')}
              >
                <ImageIcon size={13} />
                <span>Images (C) {detail.stages.images === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.thumbnails === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('thumbnails')}
              >
                <Sparkles size={13} />
                <span>Thumbnail (F) {detail.stages.thumbnails === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.assembly === 'done' ? 'btn-outline' : 'btn-success'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('assembly')}
              >
                <Film size={13} />
                <span>Assemble (G) {detail.stages.assembly === 'done' ? '✓' : ''}</span>
              </button>
            </div>

            {/* Navigation Tabs */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
              <button
                className={`nav-btn ${activeTab === 'storyboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('storyboard')}
              >
                Storyboard Scenes ({(detail.scenes || []).length})
              </button>
              <button
                className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Script & Chalkboard
              </button>
              <button
                className={`nav-btn ${activeTab === 'youtube' ? 'active' : ''}`}
                onClick={() => setActiveTab('youtube')}
              >
                YouTube Metadata
              </button>
              <button
                className={`nav-btn ${activeTab === 'media' ? 'active' : ''}`}
                onClick={() => setActiveTab('media')}
              >
                Media Players
              </button>
            </div>

            {/* Tab: Storyboard (Editable General Prompt + Scene Prompts) */}
            {activeTab === 'storyboard' && (
              <div>
                {/* General Scene Anchor Prompt Card */}
                <div
                  style={{
                    marginBottom: '20px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sparkles size={16} color="var(--accent)" />
                      <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        General Scene Anchor Prompt
                      </span>
                    </div>
                    <span
                      className="brand-badge"
                      style={{
                        background: detail.stages.images === 'done' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: detail.stages.images === 'done' ? 'var(--success)' : '#f59e0b',
                        border: `1px solid ${detail.stages.images === 'done' ? 'var(--success)' : '#f59e0b'}`,
                        fontSize: '11px',
                        textTransform: 'uppercase',
                      }}
                    >
                      {detail.stages.images === 'done' ? 'Images Ready (Done)' : 'Image Generation Pending'}
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      lineHeight: '1.4',
                      background: 'rgba(56, 189, 248, 0.08)',
                      border: '1px solid rgba(56, 189, 248, 0.2)',
                      padding: '8px 12px',
                      borderRadius: '6px',
                    }}
                  >
                    💡 <strong>Visual Story World Rule:</strong> If you edit and save a new version of the general prompt, 
                    the script's <code>image_generation</code> status automatically switches to <strong>pending</strong>. 
                    When you click <strong>Images (C)</strong>, the LLM will automatically re-generate all specific scene prompts aligned with the new story world before creating images.
                  </div>

                  {generalPromptStatus && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '10px 14px',
                        borderRadius: '6px',
                        background: generalPromptStatus.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        border: `1px solid ${generalPromptStatus.type === 'success' ? 'var(--success)' : 'var(--danger, #ef4444)'}`,
                        color: generalPromptStatus.type === 'success' ? 'var(--success)' : '#f87171',
                        fontSize: '13px',
                        fontWeight: 500,
                      }}
                    >
                      {generalPromptStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                      <span>{generalPromptStatus.message}</span>
                    </div>
                  )}

                  <textarea
                    rows={5}
                    className="search-input"
                    style={{
                      width: '100%',
                      fontSize: '13px',
                      lineHeight: '1.5',
                      fontFamily: 'inherit',
                      resize: 'vertical',
                    }}
                    value={editGeneralPrompt}
                    onChange={(e) => setEditGeneralPrompt(e.target.value)}
                    placeholder="Enter the general anchor prompt that sets the visual world, lighting, character consistency, and atmosphere..."
                  />

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {editGeneralPrompt.length} characters
                      {editGeneralPrompt.trim() !== (detail.general_prompt || '').trim() && (
                        <span style={{ color: '#f59e0b', marginLeft: '8px' }}>● Unsaved changes (new version)</span>
                      )}
                    </span>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline"
                        onClick={handleGeminiAudit}
                        disabled={auditingGemini || savingGeneralPrompt}
                        title="Audit and diversify general prompt with Gemini AI to eliminate repetition"
                        style={{ borderColor: '#8b5cf6', color: '#8b5cf6' }}
                      >
                        <Sparkles size={13} className={auditingGemini ? 'spin' : ''} />
                        <span>{auditingGemini ? 'Auditing with Gemini...' : '✨ Gemini Auditor'}</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline"
                        onClick={() => {
                          setEditGeneralPrompt(detail.general_prompt || '')
                          setGeneralPromptStatus(null)
                        }}
                        disabled={savingGeneralPrompt || auditingGemini}
                        title="Revert to last saved general prompt"
                      >
                        <RefreshCw size={13} />
                        <span>Reset</span>
                      </button>
                      <button
                        type="button"
                        className={`btn btn-sm ${
                          editGeneralPrompt.trim() !== (detail.general_prompt || '').trim()
                            ? 'btn-primary'
                            : 'btn-outline'
                        }`}
                        onClick={handleSaveGeneralPrompt}
                        disabled={savingGeneralPrompt || auditingGemini}
                      >
                        <Save size={13} />
                        <span>
                          {savingGeneralPrompt
                            ? 'Saving...'
                            : editGeneralPrompt.trim() !== (detail.general_prompt || '').trim()
                            ? 'Save New Version (Sets Images Pending)'
                            : 'Save General Prompt'}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Section header for scenes */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                    Scene Storyboard & Specific Prompts ({(detail.scenes || []).length})
                  </h3>
                  {detail.stages.images === 'pending' && (
                    <span style={{ fontSize: '12px', color: '#f59e0b' }}>
                      Pending generation: Run <strong>Images (C)</strong> above to render
                    </span>
                  )}
                </div>

                {/* Scene Cards */}
                {(detail.scenes || []).map((sc, idx) => {
                  const imgUrl = sc.image_file ? getMediaUrl(sc.image_file) : null
                  const currentPrompt = editScenePrompts[sc.scene_type] ?? sc.prompt ?? ''
                  const isSavingThisScene = savingSceneType === sc.scene_type
                  const promptModified = currentPrompt !== (sc.prompt || '')

                  return (
                    <div key={idx} className="storyboard-card">
                      <div className="storyboard-thumb">
                        {imgUrl && detail.stages.images === 'done' ? (
                          <a href={imgUrl} target="_blank" rel="noreferrer" title="Click to view full image">
                            <img src={imgUrl} alt={sc.scene_type} loading="lazy" />
                          </a>
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', padding: '8px' }}>
                            <ImageIcon size={22} style={{ margin: '0 auto 4px auto' }} />
                            <div>Pending Render</div>
                          </div>
                        )}
                      </div>

                      <div className="storyboard-body" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="brand-badge">{sc.label || sc.scene_type}</span>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Scene {idx + 1}</span>
                        </div>

                        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-main)', marginTop: '4px' }}>
                          "{sc.voice_line}"
                        </div>

                        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px', marginTop: '8px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>
                              ComfyUI Scene Prompt:
                            </span>
                            {promptModified && (
                              <button
                                type="button"
                                className="btn btn-sm btn-primary"
                                style={{ fontSize: '11px', padding: '2px 8px' }}
                                onClick={() => handleSaveScenePrompt(sc.scene_type)}
                                disabled={isSavingThisScene}
                              >
                                <Save size={11} />
                                <span>{isSavingThisScene ? 'Saving...' : 'Save Prompt'}</span>
                              </button>
                            )}
                          </div>
                          <textarea
                            rows={3}
                            className="search-input"
                            style={{
                              width: '100%',
                              fontSize: '12px',
                              fontStyle: 'italic',
                              lineHeight: '1.4',
                              resize: 'vertical',
                            }}
                            value={currentPrompt}
                            onChange={(e) => {
                              const val = e.target.value
                              setEditScenePrompts((prev) => ({ ...prev, [sc.scene_type]: val }))
                            }}
                            placeholder={
                              detail.stages.images === 'pending'
                                ? "Pending: The LLM will automatically generate this prompt when you run Images (C)..."
                                : "Enter scene-specific illustration prompt..."
                            }
                          />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Tab: Script & Chalkboard (Editable) */}
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Save Feedback Banner */}
                {saveStatus && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 14px',
                      borderRadius: '6px',
                      background: saveStatus.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      border: `1px solid ${saveStatus.type === 'success' ? 'var(--success)' : 'var(--danger, #ef4444)'}`,
                      color: saveStatus.type === 'success' ? 'var(--success)' : '#f87171',
                      fontSize: '13px',
                      fontWeight: 500,
                    }}
                  >
                    {saveStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                    <span>{saveStatus.message}</span>
                  </div>
                )}

                {/* Action Bar */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    Edit the script dialogues and chalkboard content below. Changes persist directly into the script's JSON state file.
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={handleResetEditor}
                      disabled={savingScript}
                      title="Discard unsaved changes and reload from state"
                    >
                      <RefreshCw size={13} />
                      <span>Reset</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={handleSaveScriptAndChalkboard}
                      disabled={savingScript}
                    >
                      <Save size={13} />
                      <span>{savingScript ? 'Saving to JSON...' : 'Save Changes to State'}</span>
                    </button>
                  </div>
                </div>

                {/* Section 1: Chalkboard Content */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Chalkboard Content (Image Definition)
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Used for thumbnail & Scene 2 chalkboard
                    </span>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Chalkboard Title / Target Expression
                    </label>
                    <input
                      type="text"
                      className="search-input"
                      style={{ width: '100%', fontSize: '14px' }}
                      value={chalkboardTitle}
                      onChange={(e) => setChalkboardTitle(e.target.value)}
                      placeholder="e.g. Tomar el pelo / avoir de la chance"
                    />
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                      Appears on the video thumbnail and props inside classroom scenes.
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Chalkboard Quiz Exercise / Prompt (Scene 2 Image)
                    </label>
                    <textarea
                      rows={4}
                      className="search-input"
                      style={{ width: '100%', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.5', resize: 'vertical' }}
                      value={chalkboardExercise}
                      onChange={(e) => setChalkboardExercise(e.target.value)}
                      placeholder="e.g. ¿Qué significa exactamente la frase me estás tomando el pelo?&#10;A: Te estás burlando de mí.&#10;B: Me estás peinando.&#10;C: Me estás diciendo la verdad."
                    />
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                      Defines the text drawn on the image chalkboard for quiz/game scenes.
                    </div>
                  </div>
                </div>

                {/* Section 2: Script Content */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Script & Dialogues
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={() => setJsonMode(!jsonMode)}
                      style={{ fontSize: '11px', padding: '4px 8px' }}
                    >
                      {jsonMode ? <Edit3 size={12} /> : <Code size={12} />}
                      <span>{jsonMode ? 'Switch to Form Fields' : 'Switch to Raw JSON'}</span>
                    </button>
                  </div>

                  {jsonMode ? (
                    <div>
                      <textarea
                        rows={12}
                        className="search-input"
                        style={{
                          width: '100%',
                          fontFamily: 'monospace',
                          fontSize: '12px',
                          lineHeight: '1.5',
                          background: 'var(--bg-main)',
                          resize: 'vertical',
                        }}
                        value={rawJsonText}
                        onChange={(e) => setRawJsonText(e.target.value)}
                      />
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Edit the full JSON document directly. Syntax will be verified before saving.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {Object.keys(scriptFields).length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic', padding: '10px 0' }}>
                          No script fields found. Switch to Raw JSON view to add lines.
                        </div>
                      ) : (
                        Object.entries(scriptFields).map(([key, val]) => {
                          const isShort = key.toLowerCase() === 'title' || key.toLowerCase() === 'answer'
                          const stringVal = typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val ?? '')
                          return (
                            <div key={key}>
                              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '3px', textTransform: 'capitalize' }}>
                                {key.replace(/_/g, ' ')}
                              </label>
                              {isShort ? (
                                <input
                                  type="text"
                                  className="search-input"
                                  style={{ width: '100%', fontSize: '13px' }}
                                  value={stringVal}
                                  onChange={(e) => handleFieldChange(key, e.target.value)}
                                />
                              ) : (
                                <textarea
                                  rows={2}
                                  className="search-input"
                                  style={{ width: '100%', fontSize: '13px', resize: 'vertical' }}
                                  value={stringVal}
                                  onChange={(e) => handleFieldChange(key, e.target.value)}
                                />
                              )}
                            </div>
                          )
                        })
                      )}
                    </div>
                  )}
                </div>

                {/* Bottom Save Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSaveScriptAndChalkboard}
                    disabled={savingScript}
                    style={{ padding: '8px 18px', fontWeight: 600 }}
                  >
                    <Save size={15} />
                    <span>{savingScript ? 'Saving to JSON...' : 'Save Changes to State'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Tab: YouTube Metadata */}
            {activeTab === 'youtube' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {detail.youtube_metadata ? (
                  <>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>YouTube Video Title:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.title || '', 'title')}
                        >
                          {copiedKey === 'title' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'title' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.title}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Description:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.description || '', 'desc')}
                        >
                          {copiedKey === 'desc' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'desc' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <textarea
                        readOnly
                        rows={4}
                        value={detail.youtube_metadata.description}
                        className="search-input"
                        style={{ width: '100%', resize: 'vertical' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Tags (comma-separated):</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.tags || '', 'tags')}
                        >
                          {copiedKey === 'tags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'tags' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.tags}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Hashtags:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.hashtags || '', 'hashtags')}
                        >
                          {copiedKey === 'hashtags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'hashtags' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.hashtags}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>
                  </>
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>No YouTube metadata found for this script.</div>
                )}
              </div>
            )}

            {/* Tab: Media Players */}
            {activeTab === 'media' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {detail.assets?.audio ? (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Master Voice Audio</h4>
                    <audio controls style={{ width: '100%' }} src={getMediaUrl(detail.assets.audio)} />
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No voice generated yet.</div>
                )}

                {detail.assets?.video && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Final Short Video</h4>
                    <video controls style={{ maxWidth: '320px', borderRadius: '8px', border: '1px solid var(--border)' }} src={getMediaUrl(detail.assets.video)} />
                  </div>
                )}

                {detail.assets?.thumbnail && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Chalkboard Thumbnail</h4>
                    <img
                      src={getMediaUrl(detail.assets.thumbnail)}
                      alt="Thumbnail"
                      style={{ maxWidth: '240px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Gemini API Key Configuration Dialog */}
        {showGeminiKeyModal && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 2000,
            }}
            onClick={() => setShowGeminiKeyModal(false)}
          >
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: '10px',
                padding: '24px',
                maxWidth: '480px',
                width: '90%',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <Sparkles size={18} style={{ color: '#8b5cf6' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>Enter Gemini API Key</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
                Your key will be securely saved locally in your private <code>main/.env</code> file (which is strictly gitignored) so it is never pushed to GitHub.
              </p>
              <input
                type="password"
                className="form-control"
                placeholder="Paste your Gemini API key (AIzaSy...)"
                value={geminiKeyInput}
                onChange={(e) => setGeminiKeyInput(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  marginBottom: '16px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  color: 'var(--text-main)',
                  fontSize: '13px',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline"
                  onClick={() => setShowGeminiKeyModal(false)}
                  disabled={savingGeminiKey}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  style={{ background: '#8b5cf6', borderColor: '#8b5cf6' }}
                  onClick={handleSaveGeminiKeyAndAudit}
                  disabled={!geminiKeyInput.trim() || savingGeminiKey}
                >
                  {savingGeminiKey ? 'Saving...' : 'Save Key & Audit Prompt'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
