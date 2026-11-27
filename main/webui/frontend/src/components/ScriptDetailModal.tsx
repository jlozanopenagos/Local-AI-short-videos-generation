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
  AlertTriangle,
  Layers,
  RefreshCw,
  Code,
  Edit3,
  FileText,
  Clock,
  CloudUpload,
  ExternalLink
} from 'lucide-react'
import type { ScriptDetail, JobStage, VoiceProvider, ElevenLabsModelId, ElevenLabsStatus } from '../types'
import {
  fetchScriptDetail,
  getMediaUrl,
  createJob,
  generateScript,
  renderChalkboard,
  renderThumbnail,
  updateScript,
  geminiAuditPrompt,
  fetchGeminiStatus,
  saveGeminiKey,
  fetchElevenLabsStatus,
  saveElevenLabsKey,
  estimateVoiceCredits,
  redoSceneImage,
  redoAllScriptImages,
  uploadScriptToDrive,
  type DriveUploadScope
} from '../api'

interface ScriptDetailModalProps {
  scriptId: string
  onClose: () => void
  onJobStarted: (jobId: string) => void
}

const CAMERA_PERSPECTIVES = [
  { label: '🎬 Wide Shot', value: 'Wide establishing eye-level shot.' },
  { label: '🔍 Close-Up', value: 'Tight 85mm portrait lens chest-up medium close-up.' },
  { label: '👤 Over-The-Shoulder', value: 'Dynamic 50mm Over-The-Shoulder (OTS) perspective.' },
  { label: '📐 Low-Angle', value: 'Low-angle 85mm heroic medium close-up.' },
  { label: '👁️ High-Angle', value: 'High-angle downward bird’s-eye perspective.' },
  { label: '🔄 Reverse 180°', value: '180° reverse-angle 85mm portrait shot with warm fill light.' },
  { label: '🏃 Dutch Angle', value: 'Dynamic tilted Dutch angle framing with energetic diagonal composition.' },
]

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
  const [pendingCharacterAnchors, setPendingCharacterAnchors] = useState<Record<string, any> | null>(null)
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
  const [editGameArchetype, setEditGameArchetype] = useState<string>('FILL_IN_THE_BLANK_SPEEDRUN')
  const [scriptFields, setScriptFields] = useState<Record<string, string>>({})
  const [jsonMode, setJsonMode] = useState(false)
  const [rawJsonText, setRawJsonText] = useState('')
  const [savingScript, setSavingScript] = useState(false)
  const [generatingScript, setGeneratingScript] = useState(false)
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Image enlargement Lightbox state
  const [enlargedImage, setEnlargedImage] = useState<{ url: string; title: string; subtitle?: string; sceneType?: string } | null>(null)

  // Chalkboard re-rendering state
  const [renderingChalkboard, setRenderingChalkboard] = useState(false)
  const [chalkboardRenderStatus, setChalkboardRenderStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Thumbnail editing & re-rendering state
  const [editThumbnailTitle, setEditThumbnailTitle] = useState('')
  const [renderingThumbnail, setRenderingThumbnail] = useState(false)
  const [thumbnailRenderStatus, setThumbnailRenderStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Scene image re-rendering state
  const [redoingSceneType, setRedoingSceneType] = useState<string | null>(null)
  const [redoingAllImages, setRedoingAllImages] = useState(false)
  const [sceneImageStatus, setSceneImageStatus] = useState<{ scene: string; type: 'success' | 'error'; message: string } | null>(null)
  const [imgCacheBuster, setImgCacheBuster] = useState<number>(Date.now())

  // Google Drive upload state
  const [uploadingDriveScope, setUploadingDriveScope] = useState<DriveUploadScope | null>(null)
  const uploadingDrive = uploadingDriveScope !== null
  const [driveUploadStatus, setDriveUploadStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Per-ID Voice Generation Specs (Local Qwen3-TTS vs ElevenLabs + model)
  const [voiceProvider, setVoiceProvider] = useState<VoiceProvider>('auto')
  const [elevenLabsModel, setElevenLabsModel] = useState<ElevenLabsModelId>('eleven_v3')
  const [voiceRecast, setVoiceRecast] = useState(false)
  const [elevenLabsStatus, setElevenLabsStatus] = useState<ElevenLabsStatus | null>(null)
  const [estimatedVoiceCredits, setEstimatedVoiceCredits] = useState<{ provider: string; credits: number } | null>(null)
  const [showElevenLabsKeyModal, setShowElevenLabsKeyModal] = useState(false)
  const [elevenLabsKeyInput, setElevenLabsKeyInput] = useState('')
  const [savingElevenLabsKey, setSavingElevenLabsKey] = useState(false)

  // Escape key listener for image lightbox
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && enlargedImage) {
        setEnlargedImage(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [enlargedImage])

  const isGameScript =
    detail?.video_type?.toUpperCase() === 'GAME' ||
    (detail?.id ? detail.id.length >= 2 && detail.id.charAt(1).toUpperCase() === 'G' : false)

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

    // 2. Chalkboard, Thumbnail & Game Archetype
    const titleVal = data.chalkboard_title || data.target_expression || data.title || ''
    setChalkboardTitle(titleVal)
    setChalkboardExercise(data.chalkboard_exercise || '')
    setEditThumbnailTitle(data.thumbnail_title || titleVal)
    setEditGameArchetype(data.game_archetype || 'FILL_IN_THE_BLANK_SPEEDRUN')

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

  useEffect(() => {
    fetchElevenLabsStatus(true)
      .then((st) => setElevenLabsStatus(st))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!detail?.id) return
    let cancelled = false
    estimateVoiceCredits([detail.id], voiceProvider, elevenLabsModel)
      .then((res) => {
        if (cancelled) return
        const item = res.items[0]
        setEstimatedVoiceCredits(
          item ? { provider: item.provider, credits: item.estimated_credits } : null
        )
      })
      .catch(() => {
        if (!cancelled) setEstimatedVoiceCredits(null)
      })
    return () => {
      cancelled = true
    }
  }, [detail?.id, voiceProvider, elevenLabsModel])

  const handleSaveElevenLabsKey = async () => {
    if (!elevenLabsKeyInput.trim()) return
    setSavingElevenLabsKey(true)
    try {
      await saveElevenLabsKey(elevenLabsKeyInput.trim())
      setElevenLabsKeyInput('')
      setShowElevenLabsKeyModal(false)
      const st = await fetchElevenLabsStatus(true)
      setElevenLabsStatus(st)
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err))
    } finally {
      setSavingElevenLabsKey(false)
    }
  }

  const handleRunStage = async (stage: JobStage) => {
    setTriggeringStage(stage)
    try {
      const options: Record<string, any> = { force: true }
      if (stage === 'images' && (editGeneralPrompt.trim() || (detail?.general_prompt || '').trim())) {
        options.preserve_general_prompt = true
      }
      if (stage === 'voice') {
        options.voice_provider = voiceProvider
        options.elevenlabs_model = elevenLabsModel
        options.recast = voiceRecast
      }
      const job = await createJob(stage, [scriptId], options)
      onJobStarted(job.job_id)
      onClose()
    } catch (err) {
      alert(`Could not start ${stage}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setTriggeringStage(null)
    }
  }

  const handleRegenerateScriptInPlace = async () => {
    setGeneratingScript(true)
    setSaveStatus(null)
    try {
      if (isGameScript) {
        await updateScript(scriptId, {
          game_archetype: editGameArchetype,
          chalkboard_title: chalkboardTitle,
          chalkboard_exercise: chalkboardExercise,
        })
      }
      const resp = await generateScript(scriptId, { force: true })
      setSaveStatus({
        type: 'success',
        message: `🤖 LLM script generation started (#${resp.job_id}). Updating state...`,
      })

      // Poll until completed and refresh state
      let attempts = 0
      const pollTimer = setInterval(async () => {
        attempts++
        try {
          const updated = await fetchScriptDetail(scriptId)
          if (updated.stages.scripts === 'done' || attempts >= 25) {
            clearInterval(pollTimer)
            setDetail(updated)
            populateEditorState(updated)
            setGeneratingScript(false)
            setSaveStatus({
              type: 'success',
              message: '✓ Script regenerated successfully! Entire JSON state reloaded.',
            })
            setTimeout(() => setSaveStatus(null), 6000)
          }
        } catch {
          if (attempts >= 25) {
            clearInterval(pollTimer)
            setGeneratingScript(false)
          }
        }
      }, 1500)
    } catch (err) {
      setSaveStatus({
        type: 'error',
        message: `Script generation failed: ${err instanceof Error ? err.message : String(err)}`,
      })
      setGeneratingScript(false)
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
      const res = await geminiAuditPrompt(scriptId, editGeneralPrompt, apiKeyOverride)
      setEditGeneralPrompt(res.audited_prompt)
      if (res.character_anchors) {
        setPendingCharacterAnchors(res.character_anchors)
      }
      setGeneralPromptStatus({
        type: 'success',
        message: '✨ Fresh draft generated by Gemini! Review the new visual world below. Click "Save General Prompt" to apply, or "Reset" to revert.',
      })
      setTimeout(() => {
        setGeneralPromptStatus(null)
      }, 10000)
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
        ...(pendingCharacterAnchors ? { character_anchors: pendingCharacterAnchors } : {}),
      })
      setDetail(updated)
      setPendingCharacterAnchors(null)
      populateEditorState(updated)

      if (isNewVersion) {
        setGeneralPromptStatus({
          type: 'success',
          message: '✓ Saved! General prompt updated and Image Generation marked as PENDING. Existing images are preserved. Click "Images (C)" in the header to re-generate scene prompts & images.',
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

  const applyPerspectiveToScene = (sceneType: string, perspectiveText: string) => {
    setEditScenePrompts((prev) => {
      const existing = (prev[sceneType] ?? '').trim()
      if (!existing) {
        return { ...prev, [sceneType]: perspectiveText }
      }
      return { ...prev, [sceneType]: `${perspectiveText} ${existing}` }
    })
  }

  const handleSaveScenePrompt = async (sceneType: string) => {
    setSavingSceneType(sceneType)
    setSceneImageStatus(null)
    try {
      const updated = await updateScript(scriptId, {
        image_prompts: {
          [sceneType]: editScenePrompts[sceneType] || '',
        },
      })
      setDetail(updated)
      populateEditorState(updated)
      setSceneImageStatus({
        scene: sceneType,
        type: 'success',
        message: `✓ Specific prompt for '${sceneType}' saved to JSON state! (Other scenes and general prompt untouched)`,
      })
      setTimeout(() => setSceneImageStatus(null), 5000)
    } catch (err) {
      setSceneImageStatus({
        scene: sceneType,
        type: 'error',
        message: `Failed to save prompt for ${sceneType}: ${err instanceof Error ? err.message : String(err)}`,
      })
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
        ...(isGameScript ? { game_archetype: editGameArchetype } : {}),
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

  const handleRerenderChalkboard = async () => {
    if (!detail) return
    setRenderingChalkboard(true)
    setChalkboardRenderStatus(null)
    try {
      const res = await renderChalkboard(detail.id, chalkboardExercise)
      if (res.script) {
        setDetail(res.script)
        populateEditorState(res.script)
      } else {
        const reloaded = await fetchScriptDetail(detail.id)
        setDetail(reloaded)
        populateEditorState(reloaded)
      }
      setImgCacheBuster(Date.now())
      setChalkboardRenderStatus({
        type: 'success',
        message: '✓ Chalkboard challenge image rendered and updated!',
      })
      setTimeout(() => {
        setChalkboardRenderStatus(null)
      }, 5000)
    } catch (err) {
      setChalkboardRenderStatus({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setRenderingChalkboard(false)
    }
  }

  const handleRedoSceneImage = async (sceneType: string) => {
    if (!detail) return
    setRedoingSceneType(sceneType)
    setSceneImageStatus(null)
    try {
      const promptToUse = editScenePrompts[sceneType] || undefined
      // Auto-save the specific prompt if modified so JSON state is persisted before generation
      if (promptToUse) {
        await updateScript(detail.id, {
          image_prompts: {
            [sceneType]: promptToUse,
          },
        })
      }
      const res = await redoSceneImage(detail.id, sceneType, { prompt: promptToUse })
      if (res.job_id) {
        onJobStarted(res.job_id)
        setSceneImageStatus({
          scene: sceneType,
          type: 'success',
          message: `✓ Scene '${sceneType}' image regeneration queued in Job Manager (#${res.job_id})! Track live in Queue tab or queue more scenes.`,
        })
      } else {
        setSceneImageStatus({
          scene: sceneType,
          type: 'success',
          message: `✓ Scene '${sceneType}' image regeneration initiated!`,
        })
      }
      setTimeout(() => {
        setSceneImageStatus(null)
      }, 8000)
    } catch (err) {
      setSceneImageStatus({
        scene: sceneType,
        type: 'error',
        message: `Failed to queue image for '${sceneType}': ${err instanceof Error ? err.message : String(err)}`,
      })
    } finally {
      setRedoingSceneType(null)
    }
  }

  const handleRedoAllImages = async () => {
    if (!detail) return
    setRedoingAllImages(true)
    setGeneralPromptStatus(null)
    try {
      const res = await redoAllScriptImages(detail.id, {
        general_prompt: editGeneralPrompt,
      })
      if (res.job_id) {
        onJobStarted(res.job_id)
      }
      setGeneralPromptStatus({
        type: 'success',
        message: `✓ full image redo queued in job queue (#${res.job_id})! Llama will first regenerate all specific prompts to follow this general prompt, followed by ComfyUI rendering all scene images.`,
      })
      // Reload script detail to reflect pending stages and cleared images
      const reloaded = await fetchScriptDetail(detail.id)
      setDetail(reloaded)
      populateEditorState(reloaded)
      setImgCacheBuster(Date.now())

      setTimeout(() => {
        setGeneralPromptStatus(null)
      }, 9000)
    } catch (err) {
      setGeneralPromptStatus({
        type: 'error',
        message: `failed to queue full image redo: ${err instanceof Error ? err.message : String(err)}`,
      })
    } finally {
      setRedoingAllImages(false)
    }
  }

  const handleRenderThumbnail = async () => {
    if (!detail) return
    setRenderingThumbnail(true)
    setThumbnailRenderStatus(null)
    try {
      const res = await renderThumbnail(detail.id, editThumbnailTitle)
      if (res.script) {
        setDetail(res.script)
        populateEditorState(res.script)
      } else {
        const reloaded = await fetchScriptDetail(detail.id)
        setDetail(reloaded)
        populateEditorState(reloaded)
      }
      setImgCacheBuster(Date.now())
      setThumbnailRenderStatus({
        type: 'success',
        message: `✓ Thumbnail re-rendered with text: "${res.thumbnail_title}"`,
      })
      setTimeout(() => {
        setThumbnailRenderStatus(null)
      }, 6000)
    } catch (err) {
      setThumbnailRenderStatus({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setRenderingThumbnail(false)
    }
  }

  const handleUploadToDrive = async (scope: DriveUploadScope = 'all') => {
    if (!detail) return
    setUploadingDriveScope(scope)
    setDriveUploadStatus(null)
    try {
      const res = await uploadScriptToDrive(detail.id, scope)
      const what =
        scope === 'video'
          ? 'video'
          : scope === 'thumbnail'
          ? 'thumbnail(s)'
          : 'video & thumbnail(s)'
      setDriveUploadStatus({
        type: 'success',
        message: `✓ ${what} uploaded to Drive (${res.data.language}/${res.data.video_type}/${detail.id}/)!`,
      })
      const reloaded = await fetchScriptDetail(detail.id)
      setDetail(reloaded)
      populateEditorState(reloaded)
    } catch (err) {
      setDriveUploadStatus({
        type: 'error',
        message: `failed to upload ${scope === 'all' ? '' : `${scope} `}to Google Drive: ${err instanceof Error ? err.message : String(err)}`,
      })
    } finally {
      setUploadingDriveScope(null)
    }
  }

  const handleResetEditor = () => {
    if (detail) {
      populateEditorState(detail)
      setPendingCharacterAnchors(null)
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
                <span className="icon-sand" style={{ fontFamily: 'var(--font-mono)' }}>[{detail.script_id}]</span> {detail.title || detail.topic}
              </h2>
              <span className="brand-badge badge-sand">
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
                run pipeline:
              </span>
              <button
                className={`btn btn-sm ${detail.stages.scripts === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null || generatingScript}
                onClick={() => handleRunStage('scripts')}
                title="generate or redo script dialogues (stage A)"
              >
                <FileText size={13} />
                <span>script {detail.stages.scripts === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.voice === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null || generatingScript}
                onClick={() => handleRunStage('voice')}
                title="generate voiceover narration (stage B)"
              >
                <Mic size={13} />
                <span>voice {detail.stages.voice === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.images === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('images')}
                title="generate scene images (stage C)"
              >
                <ImageIcon size={13} />
                <span>images {detail.stages.images === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.thumbnails === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('thumbnails')}
                title="generate thumbnail card (stage F)"
              >
                <Sparkles size={13} />
                <span>thumbnail {detail.stages.thumbnails === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.assembly === 'done' ? 'btn-outline' : 'btn-success'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('assembly')}
                title="assemble final short video (stage G)"
              >
                <Film size={13} />
                <span>assemble video {detail.stages.assembly === 'done' ? '✓' : ''}</span>
              </button>

              {/* Google Drive Upload Actions */}
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
                {Boolean((detail.assets as any)?.drive_folder_url || (detail as any).drive_folder_url) && (
                  <a
                    href={(detail.assets as any)?.drive_folder_url || (detail as any).drive_folder_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-sm btn-outline"
                    title="open script folder on google drive"
                    style={{
                      borderColor: '#10b981',
                      color: '#10b981',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      textDecoration: 'none',
                    }}
                  >
                    <ExternalLink size={13} />
                    <span>view on drive</span>
                  </a>
                )}
                {detail.stages.assembly === 'done' && (
                  <button
                    className="btn btn-sm"
                    disabled={uploadingDrive}
                    onClick={() => handleUploadToDrive('all')}
                    title="upload final video and thumbnail to google drive"
                    style={{
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      color: '#ffffff',
                      border: 'none',
                      fontWeight: 600,
                      boxShadow: '0 2px 6px rgba(16, 185, 129, 0.35)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <CloudUpload size={13} className={uploadingDriveScope === 'all' ? 'spin' : ''} />
                    <span>
                      {uploadingDriveScope === 'all'
                        ? 'uploading to drive...'
                        : (detail.assets as any)?.drive_folder_url || (detail as any).drive_folder_url
                        ? 're-upload to drive'
                        : 'upload to drive'}
                    </span>
                  </button>
                )}
              </div>
            </div>

            {/* Google Drive Upload Status Alert */}
            {driveUploadStatus && (
              <div
                className={`sheets-alert ${driveUploadStatus.type}`}
                style={{ marginBottom: '16px', fontSize: '13px' }}
              >
                {driveUploadStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                <span>{driveUploadStatus.message}</span>
              </div>
            )}

            {/* Navigation Tabs */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
              <button
                className={`nav-btn ${activeTab === 'storyboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('storyboard')}
              >
                storyboard scenes ({(detail.scenes || []).length})
              </button>
              <button
                className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                script & chalkboard
              </button>
              <button
                className={`nav-btn ${activeTab === 'youtube' ? 'active' : ''}`}
                onClick={() => setActiveTab('youtube')}
              >
                YouTube metadata
              </button>
              <button
                className={`nav-btn ${activeTab === 'media' ? 'active' : ''}`}
                onClick={() => setActiveTab('media')}
              >
                media players
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
                      <Sparkles size={16} className="icon-accent" />
                      <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)' }}>
                        general scene anchor prompt
                      </span>
                    </div>
                    <span
                      className="brand-badge"
                      style={{
                        background: detail.stages.images === 'done' ? 'var(--success-bg)' : 'var(--warning-bg)',
                        color: detail.stages.images === 'done' ? 'var(--success)' : 'var(--warning)',
                        border: `1px solid ${detail.stages.images === 'done' ? 'var(--success-border)' : 'var(--warning-border)'}`,
                        fontSize: '11px',
                      }}
                    >
                      {detail.stages.images === 'done' ? 'Images ready' : 'Image generation pending'}
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      lineHeight: '1.4',
                      background: 'var(--accent-subtle)',
                      border: '1px solid var(--accent-border)',
                      padding: '8px 12px',
                      borderRadius: '6px',
                    }}
                  >
                    💡 <strong>Visual story world rule:</strong> If you edit and save a new version of the general prompt, 
                    the script's <code>image_generation</code> status automatically switches to <strong>pending</strong>. 
                    When you run <strong>Images</strong>, the LLM will automatically regenerate all specific scene prompts aligned with the new story world before creating images.
                  </div>

                  {generalPromptStatus && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '10px 14px',
                        borderRadius: '6px',
                        background: generalPromptStatus.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
                        border: `1px solid ${generalPromptStatus.type === 'success' ? 'var(--success-border)' : 'var(--danger-border)'}`,
                        color: generalPromptStatus.type === 'success' ? 'var(--success)' : 'var(--danger)',
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
                        <span style={{ color: '#f59e0b', marginLeft: '8px' }}>● unsaved changes (new version)</span>
                      )}
                    </span>

                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline"
                        onClick={handleGeminiAudit}
                        disabled={auditingGemini || savingGeneralPrompt || redoingAllImages}
                        title="audit and diversify general prompt with Gemini AI to eliminate repetition"
                        style={{ borderColor: '#8b5cf6', color: '#8b5cf6' }}
                      >
                        <Sparkles size={13} className={auditingGemini ? 'spin' : ''} />
                        <span>{auditingGemini ? 'auditing with Gemini...' : '✨ gemini auditor'}</span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline"
                        onClick={() => {
                          setEditGeneralPrompt(detail.general_prompt || '')
                          setPendingCharacterAnchors(null)
                          setGeneralPromptStatus(null)
                        }}
                        disabled={savingGeneralPrompt || auditingGemini || redoingAllImages}
                        title="revert to last saved general prompt"
                      >
                        <RefreshCw size={13} />
                        <span>reset</span>
                      </button>
                      <button
                        type="button"
                        className={`btn btn-sm ${
                          editGeneralPrompt.trim() !== (detail.general_prompt || '').trim()
                            ? 'btn-primary'
                            : 'btn-outline'
                        }`}
                        onClick={handleSaveGeneralPrompt}
                        disabled={savingGeneralPrompt || auditingGemini || redoingAllImages}
                      >
                        <Save size={13} />
                        <span>
                          {savingGeneralPrompt
                            ? 'saving...'
                            : editGeneralPrompt.trim() !== (detail.general_prompt || '').trim()
                            ? 'save new version (sets images pending)'
                            : 'save general prompt'}
                        </span>
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={handleRedoAllImages}
                        disabled={redoingAllImages || savingGeneralPrompt || auditingGemini}
                        title="save this general prompt, run Llama to regenerate all scene-specific prompts, and queue ComfyUI to render all images"
                        style={{
                          background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                          color: '#ffffff',
                          border: 'none',
                          fontWeight: 600,
                          boxShadow: '0 2px 6px rgba(245, 158, 11, 0.35)',
                        }}
                      >
                        <RefreshCw size={13} className={redoingAllImages ? 'spin' : ''} />
                        <span>{redoingAllImages ? 'queueing redo...' : 'queue redo (all images)'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Section header for scenes */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                    scene storyboard & specific prompts ({(detail.scenes || []).length})
                  </h3>
                  {detail.stages.images === 'pending' && (
                    <span style={{ fontSize: '12px', color: '#f59e0b' }}>
                      pending generation: run <strong>images (stage C)</strong> above to render
                    </span>
                  )}
                </div>

                {/* Chalkboard Feedback Alert */}
                {chalkboardRenderStatus && (
                  <div
                    className={`sheets-alert ${chalkboardRenderStatus.type}`}
                    style={{ marginBottom: '12px', fontSize: '13px' }}
                  >
                    {chalkboardRenderStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                    <span>{chalkboardRenderStatus.message}</span>
                  </div>
                )}

                {/* Scene Image Feedback Alert */}
                {sceneImageStatus && (
                  <div
                    className={`sheets-alert ${sceneImageStatus.type === 'success' ? 'success' : 'error'}`}
                    style={{ marginBottom: '12px', fontSize: '13px' }}
                  >
                    {sceneImageStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                    <span>{sceneImageStatus.message}</span>
                  </div>
                )}

                {/* Scene Cards */}
                {(detail.scenes || []).map((sc, idx) => {
                  const rawImg = sc.image_file ? getMediaUrl(sc.image_file) : null
                  const imgUrl = rawImg ? `${rawImg}${rawImg.includes('?') ? '&' : '?'}t=${imgCacheBuster}` : null
                  const currentPrompt = editScenePrompts[sc.scene_type] ?? sc.prompt ?? ''
                  const isSavingThisScene = savingSceneType === sc.scene_type
                  const isRedoingThisScene = redoingSceneType === sc.scene_type
                  const promptModified = currentPrompt !== (sc.prompt || '')
                  const isChallengeScene = sc.scene_type.toLowerCase() === 'challenge'

                  return (
                    <div key={idx} className="storyboard-card">
                      <div className="storyboard-thumb" style={{ position: 'relative' }}>
                        {isRedoingThisScene && (
                          <div
                            style={{
                              position: 'absolute',
                              inset: 0,
                              background: 'rgba(0, 0, 0, 0.7)',
                              display: 'flex',
                              flexDirection: 'column',
                              alignItems: 'center',
                              justifyContent: 'center',
                              borderRadius: '6px',
                              color: '#fff',
                              fontSize: '11px',
                              gap: '6px',
                              zIndex: 10,
                            }}
                          >
                            <RefreshCw size={18} className="spin" />
                            <span>ComfyUI...</span>
                          </div>
                        )}
                        {imgUrl ? (
                          <div
                            className="storyboard-thumb-clickable"
                            onClick={() =>
                              setEnlargedImage({
                                url: imgUrl,
                                title: `${detail.id} - ${sc.label || sc.scene_type} (Scene ${idx + 1})`,
                                subtitle: sc.voice_line ? `"${sc.voice_line}"` : undefined,
                                sceneType: sc.scene_type,
                              })
                            }
                            title="Click to inspect enlarged image"
                            style={{
                              cursor: 'zoom-in',
                              width: '100%',
                              height: '100%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            <img src={imgUrl} alt={sc.scene_type} loading="lazy" />
                          </div>
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', padding: '8px' }}>
                            <ImageIcon size={22} style={{ margin: '0 auto 4px auto' }} />
                            <div>pending render</div>
                          </div>
                        )}
                      </div>

                      <div className="storyboard-body" style={{ width: '100%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="brand-badge">{sc.label || sc.scene_type}</span>
                            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>scene {idx + 1}</span>
                            {sc.is_static && (
                              <span
                                className="brand-badge"
                                style={{
                                  fontSize: '10.5px',
                                  background: 'rgba(56, 189, 248, 0.1)',
                                  color: '#38bdf8',
                                  borderColor: 'rgba(56, 189, 248, 0.3)',
                                }}
                              >
                                static shared asset
                              </span>
                            )}
                            {sc.is_virtual_cut && (
                              <span
                                className="brand-badge"
                                style={{
                                  fontSize: '10.5px',
                                  background: 'rgba(168, 85, 247, 0.1)',
                                  color: '#c084fc',
                                  borderColor: 'rgba(168, 85, 247, 0.3)',
                                }}
                              >
                                virtual punch-in cut (1.18x)
                              </span>
                            )}
                          </div>
                          {!sc.is_static && !sc.is_virtual_cut && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline"
                                style={{
                                  fontSize: '11px',
                                  padding: '3px 10px',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '5px',
                                  borderColor: 'var(--accent)',
                                  color: 'var(--accent)',
                                }}
                                onClick={() => handleRedoSceneImage(sc.scene_type)}
                                disabled={isRedoingThisScene || isSavingThisScene}
                                title={`queue generation for ${sc.label || sc.scene_type} in job queue tab`}
                              >
                                <Clock size={12} className={isRedoingThisScene ? 'spin' : ''} />
                                <span>{isRedoingThisScene ? 'queuing...' : 'queue image redo'}</span>
                              </button>
                            </div>
                          )}
                        </div>

                        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-main)', marginTop: '6px' }}>
                          "{sc.voice_line}"
                        </div>

                        {/* Dedicated Chalkboard Re-render Action for GAME Challenge scene */}
                        {isGameScript && isChallengeScene && (
                          <div
                            style={{
                              background: 'rgba(168, 85, 247, 0.08)',
                              border: '1px solid rgba(168, 85, 247, 0.25)',
                              borderRadius: '6px',
                              padding: '10px 12px',
                              marginTop: '8px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              gap: '12px',
                              flexWrap: 'wrap',
                            }}
                          >
                            <div>
                              <div style={{ fontSize: '12px', fontWeight: 600, color: '#c084fc' }}>
                                high-resolution game chalkboard
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                                native typography rendered on empty chalkboard (zero ComfyUI/LLM needed).
                              </div>
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm btn-primary"
                              onClick={handleRerenderChalkboard}
                              disabled={renderingChalkboard}
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                              title="re-render high-resolution chalkboard image directly from current chalkboard text"
                            >
                              <Layers size={13} />
                              <span>{renderingChalkboard ? 'rendering chalkboard...' : 'redo chalkboard image'}</span>
                            </button>
                          </div>
                        )}

                        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', marginTop: '10px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-main)' }}>
                                {sc.is_static
                                  ? 'static shared scene:'
                                  : sc.is_virtual_cut
                                  ? 'virtual cut scene note:'
                                  : isGameScript && isChallengeScene
                                  ? 'chalkboard scene note:'
                                  : 'scene specific prompt:'}
                              </span>
                              {!isChallengeScene && !sc.is_static && !sc.is_virtual_cut && (
                                <span style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'var(--bg-card)', padding: '2px 7px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                                  independent · does not affect other scenes
                                </span>
                              )}
                              {promptModified && !sc.is_static && !sc.is_virtual_cut && (
                                <span className="brand-badge" style={{ fontSize: '10.5px', background: 'var(--warning-bg)', color: 'var(--warning)', borderColor: 'var(--warning-border)' }}>
                                  ● unsaved changes
                                </span>
                              )}
                            </div>

                            {!isChallengeScene && !sc.is_static && !sc.is_virtual_cut && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {promptModified && (
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline"
                                    style={{ fontSize: '11px', padding: '3px 8px' }}
                                    onClick={() => {
                                      setEditScenePrompts((prev) => ({
                                        ...prev,
                                        [sc.scene_type]: sc.prompt || '',
                                      }))
                                    }}
                                    title="discard unsaved changes for this scene"
                                  >
                                    <span>discard</span>
                                  </button>
                                )}
                                <button
                                  type="button"
                                  className={`btn btn-sm ${promptModified ? 'btn-primary' : 'btn-outline'}`}
                                  style={{ fontSize: '11px', padding: '3px 10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                  onClick={() => handleSaveScenePrompt(sc.scene_type)}
                                  disabled={isSavingThisScene}
                                  title="save this scene specific prompt to JSON state (does not affect general prompt or other scenes)"
                                >
                                  <Save size={12} />
                                  <span>{isSavingThisScene ? 'saving...' : 'save specific prompt'}</span>
                                </button>
                              </div>
                            )}
                          </div>

                          {sc.is_static ? (
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                              this scene uses the centralized Tito waiting card (input/images/game_images). Loaded dynamically at assembly with zero physical duplication in script folders.
                            </div>
                          ) : sc.is_virtual_cut ? (
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                              this scene uses a dynamic 1.18x virtual punch-in cut from <strong>{sc.scene_type === 'dialogue_part_1' ? 'hook' : 'payoff'}</strong> during video assembly. No duplicate image is generated, preserving unique character coverage.
                            </div>
                          ) : isGameScript && isChallengeScene ? (
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '4px 0' }}>
                              scene 2 challenge is rendered directly as high-resolution chalkboard typography from the <strong>script & chalkboard</strong> tab exercise text. ComfyUI prompt does not apply to this scene.
                            </div>
                          ) : (
                            <>
                              <textarea
                                rows={4}
                                className="search-input mono-font"
                                style={{
                                  width: '100%',
                                  fontSize: '12px',
                                  lineHeight: '1.45',
                                  resize: 'vertical',
                                  padding: '8px 10px',
                                  borderRadius: '6px',
                                  fontFamily: 'monospace',
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

                              {/* Camera & Visual Perspective Helper Chips */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
                                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                                  Angle Presets:
                                </span>
                                {CAMERA_PERSPECTIVES.map((p) => (
                                  <button
                                    key={p.label}
                                    type="button"
                                    className="perspective-chip"
                                    onClick={() => applyPerspectiveToScene(sc.scene_type, p.value)}
                                    title={`Prepend framing angle: "${p.value}"`}
                                  >
                                    {p.label}
                                  </button>
                                ))}
                              </div>
                            </>
                          )}
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
                      onClick={handleRegenerateScriptInPlace}
                      disabled={generatingScript || savingScript}
                      title="Re-generate script dialogues with dedicated LLM domain engine"
                      style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
                    >
                      <Sparkles size={13} className={generatingScript ? 'animate-spin' : ''} />
                      <span>{generatingScript ? 'Generating with LLM...' : 'Re-do Script with LLM'}</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={handleResetEditor}
                      disabled={savingScript || generatingScript}
                      title="Discard unsaved changes and reload from state"
                    >
                      <RefreshCw size={13} />
                      <span>Reset</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={handleSaveScriptAndChalkboard}
                      disabled={savingScript || generatingScript}
                    >
                      <Save size={13} />
                      <span>{savingScript ? 'Saving to JSON...' : 'Save Changes to State'}</span>
                    </button>
                  </div>
                </div>

                {/* Section 1: Chalkboard Content (Only for Game 'G' scripts) */}
                {(detail.script_id.toUpperCase().startsWith('G') || detail.type?.toLowerCase() === 'game') && (
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
                      <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)' }}>
                        Game Dynamics & Chalkboard definition
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Used for Scene 2 chalkboard & game logic
                      </span>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Game Archetype (Challenge Format)
                      </label>
                      <select
                        className="search-input"
                        style={{ width: '100%', fontSize: '13px', background: 'var(--bg-card)', color: 'var(--text-main)', cursor: 'pointer' }}
                        value={editGameArchetype}
                        onChange={(e) => setEditGameArchetype(e.target.value)}
                      >
                        <option value="FALSE_FRIEND_TRAP">🎭 false friend trap (falsos amigos / faux-amis) — 3-4 options</option>
                        <option value="ODD_ONE_OUT">🔍 odd one out (el intruso / l'intrus) — 3-4 options</option>
                        <option value="SPOT_THE_MISTAKE">⚠️ spot the mistake (encuentra el error) — 3-4 options</option>
                        <option value="MINIMAL_PAIR_SHOWDOWN">🎙️ minimal pair / stress showdown (heteronyms) — 2-3 options</option>
                        <option value="FILL_IN_THE_BLANK_SPEEDRUN">⚡ fill-in-the-blank speedrun (rellena el hueco) — 3-4 options</option>
                      </select>
                      <div style={{ fontSize: '11px', color: 'var(--accent)', marginTop: '4px' }}>
                        {editGameArchetype === 'FALSE_FRIEND_TRAP' && 'Highlights deceptive literal translation traps with native contrasts.'}
                        {editGameArchetype === 'ODD_ONE_OUT' && 'Presents words sharing a hidden grammar rule, challenging the learner to spot the outlier.'}
                        {editGameArchetype === 'SPOT_THE_MISTAKE' && 'Ego challenge targeting common intermediate learner errors (prepositions, agreement).'}
                        {editGameArchetype === 'MINIMAL_PAIR_SHOWDOWN' && 'Auditory challenge distinguishing word stress (e.g. PROject vs proJECT) or minimal sounds.'}
                        {editGameArchetype === 'FILL_IN_THE_BLANK_SPEEDRUN' && 'Rapid collocation sprint testing authentic idioms under time pressure.'}
                      </div>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Chalkboard title / target expression
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
                        Chalkboard quiz exercise / prompt (Scene 2 image)
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
                )}

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

                {/* Bottom Save Buttons */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px', flexWrap: 'wrap' }}>
                  {isGameScript && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={async () => {
                        await handleSaveScriptAndChalkboard()
                        await handleRerenderChalkboard()
                      }}
                      disabled={savingScript || renderingChalkboard}
                      style={{ padding: '8px 18px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                      title="Save script & chalkboard changes to JSON and immediately re-render the chalkboard image"
                    >
                      <Sparkles size={15} />
                      <span>{renderingChalkboard ? 'Rendering Chalkboard...' : 'Save & Render Chalkboard'}</span>
                    </button>
                  )}
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
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>YouTube video title:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.title || '', 'title')}
                        >
                          {copiedKey === 'title' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'title' ? 'copied' : 'copy'}</span>
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
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>description:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.description || '', 'desc')}
                        >
                          {copiedKey === 'desc' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'desc' ? 'copied' : 'copy'}</span>
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
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>tags (comma-separated):</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.tags || '', 'tags')}
                        >
                          {copiedKey === 'tags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'tags' ? 'copied' : 'copy'}</span>
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
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>hashtags:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.hashtags || '', 'hashtags')}
                        >
                          {copiedKey === 'hashtags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'hashtags' ? 'copied' : 'copy'}</span>
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
                  <div style={{ color: 'var(--text-muted)' }}>no YouTube metadata found for this script.</div>
                )}
              </div>
            )}

            {/* Tab: Media Players */}
            {activeTab === 'media' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {driveUploadStatus && (
                  <div
                    className={`sheets-alert ${driveUploadStatus.type}`}
                    style={{ fontSize: '13px', marginBottom: 0 }}
                  >
                    {driveUploadStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                    <span>{driveUploadStatus.message}</span>
                  </div>
                )}

                {/* Master Voice Audio + Per-ID Voice Generation Specs (Local vs ElevenLabs) */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <h4 style={{ fontSize: '14px', margin: 0, color: 'var(--text-muted)' }}>master voice audio</h4>
                      {detail.voice_profile_meta?.provider === 'elevenlabs' ? (
                        <span className="brand-badge" style={{ fontSize: '11px', background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa', borderColor: 'rgba(139, 92, 246, 0.4)' }}>
                          ElevenLabs · {detail.voice_profile_meta.elevenlabs_model || 'eleven_v3'}
                          {detail.voice_profile_meta.credits_used ? ` (${detail.voice_profile_meta.credits_used} cr)` : ''}
                        </span>
                      ) : detail.assets?.audio ? (
                        <span className="brand-badge" style={{ fontSize: '11px' }}>
                          Local Qwen3-TTS
                        </span>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={() => setShowElevenLabsKeyModal(true)}
                      style={{ fontSize: '11px' }}
                    >
                      {elevenLabsStatus?.configured ? 'ElevenLabs key ✓' : 'set ElevenLabs API key'}
                    </button>
                  </div>

                  {detail.assets?.audio ? (
                    <audio controls style={{ width: '100%' }} src={getMediaUrl(detail.assets.audio)} />
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>no voice generated yet.</div>
                  )}

                  {/* Per-ID Voice Generation Specs */}
                  <div
                    style={{
                      background: 'var(--bg-main)',
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                    }}
                  >
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                      voice generation specs
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                        <span>voice provider</span>
                        <select
                          className="search-input"
                          value={voiceProvider}
                          onChange={(e) => setVoiceProvider(e.target.value as VoiceProvider)}
                        >
                          <option value="auto">Auto Hybrid (Roleplay/Expr/Facts → ElevenLabs | Game → Local)</option>
                          <option value="elevenlabs">ElevenLabs</option>
                          <option value="local">Local Qwen3-TTS</option>
                        </select>
                      </label>

                      {voiceProvider !== 'local' && (
                        <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                          <span>ElevenLabs model</span>
                          <select
                            className="search-input"
                            value={elevenLabsModel}
                            onChange={(e) => setElevenLabsModel(e.target.value as ElevenLabsModelId)}
                          >
                            <option value="eleven_v3">Eleven v3 (Most Expressive — 1 cr/char)</option>
                            <option value="eleven_multilingual_v2">Multilingual v2 (Classic Stable — 1 cr/char)</option>
                            <option value="eleven_flash_v2_5">Flash v2.5 (Budget 2x — 0.5 cr/char)</option>
                          </select>
                        </label>
                      )}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', fontSize: '12px', color: 'var(--text-muted)' }}>
                        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: 'var(--text-main)' }}>
                          <input
                            type="checkbox"
                            checked={voiceRecast}
                            onChange={(e) => setVoiceRecast(e.target.checked)}
                          />
                          <span>choose new voices</span>
                        </label>
                        {estimatedVoiceCredits && (
                          <span>
                            route: <strong>{estimatedVoiceCredits.provider === 'elevenlabs' ? `ElevenLabs (~${estimatedVoiceCredits.credits} cr)` : 'Local Qwen3-TTS (0 cr)'}</strong>
                            {estimatedVoiceCredits.provider === 'elevenlabs' && elevenLabsStatus?.subscription
                              ? ` · ${elevenLabsStatus.subscription.remaining_credits.toLocaleString()} left`
                              : ''}
                          </span>
                        )}
                      </div>

                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        disabled={triggeringStage !== null || generatingScript}
                        onClick={() => handleRunStage('voice')}
                        title="generate or redo voice using the selected provider and model"
                      >
                        <Mic size={13} />
                        <span>{triggeringStage === 'voice' ? 'queuing voice...' : 'generate / re-do voice'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Final Short Video + Standalone Video Drive Upload */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <h4 style={{ fontSize: '14px', margin: 0, color: 'var(--text-muted)' }}>final short video</h4>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                      {detail.assets?.drive_video_url && (
                        <a
                          href={detail.assets.drive_video_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-sm btn-outline"
                          style={{
                            borderColor: '#10b981',
                            color: '#10b981',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            textDecoration: 'none',
                          }}
                        >
                          <ExternalLink size={13} />
                          <span>view video on drive</span>
                        </a>
                      )}
                      {detail.assets?.video && (
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={uploadingDrive}
                          onClick={() => handleUploadToDrive('video')}
                          title="upload only the final .mp4 video to google drive (without thumbnails)"
                          style={{
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            color: '#ffffff',
                            border: 'none',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                          }}
                        >
                          <CloudUpload size={13} className={uploadingDriveScope === 'video' ? 'spin' : ''} />
                          <span>
                            {uploadingDriveScope === 'video'
                              ? 'uploading video...'
                              : detail.assets?.drive_video_url
                              ? 're-upload video only to drive'
                              : 'upload video only to drive'}
                          </span>
                        </button>
                      )}
                    </div>
                  </div>
                  {detail.assets?.video ? (
                    <video
                      controls
                      style={{ maxWidth: '320px', borderRadius: '8px', border: '1px solid var(--border)' }}
                      src={getMediaUrl(detail.assets.video)}
                    />
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>no final video assembled yet.</div>
                  )}
                </div>

                {/* Thumbnails: Content Editor + Re-render + Standalone Thumbnail Drive Upload */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <h4 style={{ fontSize: '14px', margin: 0, color: 'var(--text-muted)' }}>
                      {detail.assets?.thumbnail_variants && Object.keys(detail.assets.thumbnail_variants).length > 1
                        ? 'thumbnails (LatAm & Spain)'
                        : 'thumbnail'}
                    </h4>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                      {(detail.assets?.drive_thumbnail_url || detail.assets?.drive_folder_url || detail.drive_folder_url) && (
                        <a
                          href={detail.assets?.drive_thumbnail_url || detail.assets?.drive_folder_url || detail.drive_folder_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-sm btn-outline"
                          style={{
                            borderColor: '#10b981',
                            color: '#10b981',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            textDecoration: 'none',
                          }}
                        >
                          <ExternalLink size={13} />
                          <span>view thumbnail on drive</span>
                        </a>
                      )}
                      {(detail.assets?.thumbnail || (detail.assets?.thumbnail_variants && Object.keys(detail.assets.thumbnail_variants).length > 0)) && (
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={uploadingDrive || renderingThumbnail}
                          onClick={() => handleUploadToDrive('thumbnail')}
                          title="upload only the thumbnail image(s) to google drive (without video)"
                          style={{
                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                            color: '#ffffff',
                            border: 'none',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                          }}
                        >
                          <CloudUpload size={13} className={uploadingDriveScope === 'thumbnail' ? 'spin' : ''} />
                          <span>
                            {uploadingDriveScope === 'thumbnail'
                              ? 'uploading thumbnail...'
                              : detail.assets?.drive_thumbnail_url
                              ? 're-upload thumbnail(s) to drive'
                              : 'upload thumbnail(s) to drive'}
                          </span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Thumbnail Text Content Editor */}
                  <div
                    style={{
                      background: 'var(--bg-main)',
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
                        thumbnail text content
                      </label>
                      {editThumbnailTitle.trim() !== (detail.thumbnail_title || '').trim() && (
                        <span style={{ fontSize: '11px', color: '#f59e0b' }}>● unsaved edits</span>
                      )}
                    </div>
                    <input
                      type="text"
                      className="search-input"
                      style={{ width: '100%', fontSize: '13px' }}
                      value={editThumbnailTitle}
                      onChange={(e) => setEditThumbnailTitle(e.target.value)}
                      placeholder="Enter text rendered on the thumbnail card (leave blank to reset to script title)..."
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Tip: Use <code>:</code> to split header and main phrase (e.g. <code>Header: Main Phrase</code>). Leave empty to revert to script title.
                      </span>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          disabled={renderingThumbnail}
                          onClick={() => {
                            setEditThumbnailTitle(detail.thumbnail_title || detail.chalkboard_title || detail.title || '')
                            setThumbnailRenderStatus(null)
                          }}
                          title="reset thumbnail text to currently saved value"
                        >
                          <RefreshCw size={12} />
                          <span>reset</span>
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          disabled={renderingThumbnail}
                          onClick={handleRenderThumbnail}
                          title="save thumbnail text and immediately re-render the thumbnail image(s)"
                        >
                          <Sparkles size={12} className={renderingThumbnail ? 'spin' : ''} />
                          <span>{renderingThumbnail ? 're-doing thumbnail...' : 'save & re-do thumbnail'}</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {thumbnailRenderStatus && (
                    <div
                      className={`sheets-alert ${thumbnailRenderStatus.type}`}
                      style={{ fontSize: '13px', marginBottom: 0 }}
                    >
                      {thumbnailRenderStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                      <span>{thumbnailRenderStatus.message}</span>
                    </div>
                  )}

                  {/* Thumbnail Image Preview(s) */}
                  {detail.assets?.thumbnail_variants && Object.keys(detail.assets.thumbnail_variants).length > 1 ? (
                    <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
                      {Object.entries(detail.assets.thumbnail_variants).map(([variant, thumbPath]) => {
                        const label = variant === 'latam' ? 'LatAm' : variant === 'spain' ? 'Spain' : variant
                        const src = `${getMediaUrl(thumbPath)}${getMediaUrl(thumbPath).includes('?') ? '&' : '?'}t=${imgCacheBuster}`
                        return (
                          <div key={variant} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
                            <img
                              src={src}
                              alt={`Thumbnail ${label}`}
                              onClick={() =>
                                setEnlargedImage({
                                  url: src,
                                  title: `${detail.id} - Thumbnail (${label})`,
                                  subtitle: detail.title,
                                })
                              }
                              title={`Click to view enlarged ${label} thumbnail`}
                              style={{ maxWidth: '180px', borderRadius: '8px', border: '1px solid var(--border)', cursor: 'zoom-in' }}
                            />
                          </div>
                        )
                      })}
                    </div>
                  ) : detail.assets?.thumbnail ? (
                    <div>
                      <img
                        src={`${getMediaUrl(detail.assets.thumbnail!)}${getMediaUrl(detail.assets.thumbnail!).includes('?') ? '&' : '?'}t=${imgCacheBuster}`}
                        alt="Thumbnail"
                        onClick={() =>
                          setEnlargedImage({
                            url: `${getMediaUrl(detail.assets.thumbnail!)}${getMediaUrl(detail.assets.thumbnail!).includes('?') ? '&' : '?'}t=${imgCacheBuster}`,
                            title: `${detail.id} - Thumbnail`,
                            subtitle: detail.title,
                          })
                        }
                        title="Click to view enlarged thumbnail"
                        style={{ maxWidth: '240px', borderRadius: '8px', border: '1px solid var(--border)', cursor: 'zoom-in' }}
                      />
                    </div>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                      no thumbnail rendered yet. Edit the text above and click <strong>save &amp; re-do thumbnail</strong>.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* High-Resolution Image Lightbox Overlay */}
        {enlargedImage && (
          <div
            className="image-lightbox-overlay"
            onClick={() => setEnlargedImage(null)}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.90)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              zIndex: 99999,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px',
            }}
          >
            <div
              style={{
                position: 'relative',
                maxWidth: '92vw',
                maxHeight: '92vh',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Lightbox Header */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  width: '100%',
                  marginBottom: '12px',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: '16px', letterSpacing: '-0.01em' }}>
                    {enlargedImage.title}
                  </div>
                  {enlargedImage.subtitle && (
                    <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px', maxWidth: '700px' }}>
                      {enlargedImage.subtitle}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {enlargedImage.sceneType && (
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => {
                        if (enlargedImage.sceneType) {
                          handleRedoSceneImage(enlargedImage.sceneType)
                        }
                      }}
                      disabled={redoingSceneType === enlargedImage.sceneType}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                      title="queue image regeneration in job manager"
                    >
                      <Clock size={12} className={redoingSceneType === enlargedImage.sceneType ? 'spin' : ''} />
                      <span>{redoingSceneType === enlargedImage.sceneType ? 'queuing...' : 'queue image redo'}</span>
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => setEnlargedImage(null)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.15)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '50%',
                      width: '34px',
                      height: '34px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer',
                      fontSize: '18px',
                    }}
                    title="close preview (esc)"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Lightbox Image Preview */}
              <img
                src={enlargedImage.url}
                alt={enlargedImage.title}
                style={{
                  maxHeight: '82vh',
                  maxWidth: '88vw',
                  objectFit: 'contain',
                  borderRadius: '8px',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                }}
              />
            </div>
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
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>enter Gemini API key</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
                Your key will be securely saved locally in your private <code>main/.env</code> file (which is strictly gitignored) so it is never pushed to GitHub.
              </p>
              <input
                type="password"
                className="form-control"
                placeholder="paste your Gemini API key (AIzaSy...)"
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

        {/* Secure ElevenLabs API Key Configuration Dialog */}
        {showElevenLabsKeyModal && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 2000,
            }}
            onClick={() => setShowElevenLabsKeyModal(false)}
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
                <Mic size={18} style={{ color: 'var(--accent)' }} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-main)' }}>enter ElevenLabs API key</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
                Your private key is saved strictly locally in <code>main/.env</code> (gitignored) so it is never pushed to GitHub or returned in API responses.
              </p>
              <input
                type="password"
                className="form-control"
                placeholder="paste your ElevenLabs API key (sk_...)"
                value={elevenLabsKeyInput}
                onChange={(e) => setElevenLabsKeyInput(e.target.value)}
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
                  onClick={() => setShowElevenLabsKeyModal(false)}
                  disabled={savingElevenLabsKey}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={handleSaveElevenLabsKey}
                  disabled={!elevenLabsKeyInput.trim() || savingElevenLabsKey}
                >
                  {savingElevenLabsKey ? 'Saving...' : 'Save Key to .env'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
