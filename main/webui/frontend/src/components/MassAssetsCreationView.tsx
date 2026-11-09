import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Layers,
  Mic,
  Image as ImageIcon,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  X,
  Upload,
  FileSpreadsheet,
  Trash2,
  Play,
  Filter,
  ExternalLink,
} from 'lucide-react'
import type { JobStage, SystemStatus, ValidatedScriptId, ScriptCatalogResponse } from '../types'
import { createJob, validateScriptIds, fetchScriptCatalog } from '../api'

interface MassAssetsCreationViewProps {
  system: SystemStatus | null
  onJobStarted: (jobId: string) => void
  onSelectScript: (scriptId: string) => void
}

type CollectionMode = 'text' | 'csv' | 'catalog'

export const MassAssetsCreationView: React.FC<MassAssetsCreationViewProps> = ({
  system,
  onJobStarted,
  onSelectScript,
}) => {
  // Selected Target Stage
  const [targetStage, setTargetStage] = useState<JobStage>('images')

  // Collection Mode
  const [collectionMode, setCollectionMode] = useState<CollectionMode>('text')

  // Textarea input
  const [rawIdInput, setRawIdInput] = useState<string>('')

  // Validated items
  const [validatedItems, setValidatedItems] = useState<ValidatedScriptId[]>([])
  const [isValidating, setIsValidating] = useState<boolean>(false)

  // Options
  const [forceRegenerate, setForceRegenerate] = useState<boolean>(true)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // CSV file loading state
  const [csvFileName, setCsvFileName] = useState<string | null>(null)

  // Parse raw text into unique sanitized IDs
  const parsedRawIds = useMemo(() => {
    if (!rawIdInput.trim()) return []
    const tokens = rawIdInput.split(/[\s,;\n\r\t]+/)
    const seen = new Set<string>()
    const ids: string[] = []
    for (const t of tokens) {
      const clean = t.trim().toUpperCase().replace(/^SCRIPT_/, '').replace(/\.JSON$/, '')
      if (clean && !seen.has(clean)) {
        seen.add(clean)
        ids.push(clean)
      }
    }
    return ids
  }, [rawIdInput])

  // Trigger ID validation against backend
  const handleValidate = useCallback(async (idsToValidate: string[]) => {
    if (!idsToValidate.length) {
      setValidatedItems([])
      return
    }
    setIsValidating(true)
    setErrorMessage(null)
    try {
      const res = await validateScriptIds(idsToValidate)
      setValidatedItems(res.items)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setIsValidating(false)
    }
  }, [])

  // Debounced auto-validate when typing/pasting
  useEffect(() => {
    if (!parsedRawIds.length) {
      setValidatedItems([])
      return
    }
    const timer = setTimeout(() => {
      handleValidate(parsedRawIds)
    }, 600)
    return () => clearInterval(timer)
  }, [parsedRawIds, handleValidate])

  // Valid and Invalid lists
  const validIds = useMemo(
    () => validatedItems.filter((item) => item.exists).map((item) => item.id),
    [validatedItems]
  )
  const invalidItems = useMemo(
    () => validatedItems.filter((item) => !item.exists),
    [validatedItems]
  )

  // Remove an individual ID
  const handleRemoveId = (idToRemove: string) => {
    const updated = rawIdInput
      .split(/[\s,;\n\r\t]+/)
      .filter((id) => id.trim().toUpperCase() !== idToRemove.toUpperCase())
      .join(', ')
    setRawIdInput(updated)
  }

  // Remove all invalid IDs
  const handleRemoveInvalid = () => {
    const invalidSet = new Set(invalidItems.map((i) => i.id.toUpperCase()))
    const updated = rawIdInput
      .split(/[\s,;\n\r\t]+/)
      .filter((id) => !invalidSet.has(id.trim().toUpperCase()))
      .join(', ')
    setRawIdInput(updated)
  }

  // Clear all
  const handleClearAll = () => {
    setRawIdInput('')
    setValidatedItems([])
    setCsvFileName(null)
    setErrorMessage(null)
  }

  // Quick preset loader from catalog by stage
  const handleLoadFromCatalog = async (filterKey: 'voice' | 'images' | 'thumbnails') => {
    setIsValidating(true)
    setErrorMessage(null)
    try {
      const stageFilter =
        filterKey === 'voice'
          ? 'missing_voice'
          : filterKey === 'images'
            ? 'missing_images'
            : 'all'

      const data: ScriptCatalogResponse = await fetchScriptCatalog({
        pageSize: 100,
        stageFilter,
      })

      const loadedIds = data.items.map((s) => s.id)
      if (!loadedIds.length) {
        setErrorMessage(`No scripts found with pending ${filterKey}.`)
        return
      }

      setRawIdInput(loadedIds.join(', '))
      handleValidate(loadedIds)
    } catch (err) {
      setErrorMessage(`Failed to query catalog: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsValidating(false)
    }
  }

  // Handle local CSV file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setCsvFileName(file.name)
    const reader = new FileReader()
    reader.onload = (event) => {
      const content = String(event.target?.result || '')
      const lines = content.split(/\r?\n/)
      if (!lines.length) return

      let idColIdx = 0
      const header = lines[0].split(',')
      const foundIdx = header.findIndex((h) => {
        const clean = h.trim().toUpperCase().replace(/["']/g, '')
        return clean === 'ID' || clean === 'SCRIPT_ID'
      })
      if (foundIdx !== -1) {
        idColIdx = foundIdx
      }

      const extracted: string[] = []
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim()
        if (!line) continue
        const cols = line.split(',')
        if (cols[idColIdx]) {
          const val = cols[idColIdx].trim().toUpperCase().replace(/["']/g, '')
          if (val && !extracted.includes(val)) {
            extracted.push(val)
          }
        }
      }

      if (extracted.length) {
        setRawIdInput(extracted.join(', '))
        handleValidate(extracted)
      } else {
        setErrorMessage(`No valid IDs found in CSV file "${file.name}".`)
      }
    }
    reader.readAsText(file)
  }

  // Launch Mass Asset Job
  const handleLaunch = async () => {
    if (!validIds.length) {
      setErrorMessage('Please provide at least one valid script ID.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      const job = await createJob(targetStage, validIds, {
        force: forceRegenerate,
      })
      onJobStarted(job.job_id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
      setIsSubmitting(false)
    }
  }

  const comfyOnline = system?.comfyui?.status === 'online' || (system as any)?.comfy?.status === 'online'
  const isComfyRequired = targetStage === 'images' || targetStage === 'voice'

  return (
    <div className="mass-creation-container">
      {/* View Header */}
      <div className="mass-creation-header">
        <div className="header-title-group">
          <div className="header-icon-wrap">
            <Layers size={28} className="text-blue-400" />
          </div>
          <div>
            <h1 className="header-title">Mass assets creation</h1>
            <p className="header-subtitle">
              Batch create Voice tracks, Scene Illustrations, or Chalkboard Thumbnails for arbitrary IDs across any
              language or video format with enforced re-generation.
            </p>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="sheets-alert error">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* STEP 1: Select Asset Target */}
      <div className="mass-step-card">
        <div className="step-badge-row">
          <span className="step-number">Step 1</span>
          <span className="step-heading">Choose Asset Type to Create</span>
        </div>

        <div className="asset-cards-grid">
          {/* Option A: Images */}
          <div
            className={`asset-option-card ${targetStage === 'images' ? 'selected' : ''}`}
            onClick={() => setTargetStage('images')}
          >
            <div className="option-icon-box images">
              <ImageIcon size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">Scene Images</div>
              <div className="option-desc">
                2D cartoon narrative illustrations generated through ComfyUI for all scenes in each script.
              </div>
            </div>
            <div className="option-stage-pill">Stage C</div>
          </div>

          {/* Option B: Voice */}
          <div
            className={`asset-option-card ${targetStage === 'voice' ? 'selected' : ''}`}
            onClick={() => setTargetStage('voice')}
          >
            <div className="option-icon-box voice">
              <Mic size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">Voice Files (Audio)</div>
              <div className="option-desc">
                Multi-character spoken dialogue and narration synthesized via Kokoro / ComfyUI.
              </div>
            </div>
            <div className="option-stage-pill">Stage B</div>
          </div>

          {/* Option C: Thumbnails */}
          <div
            className={`asset-option-card ${targetStage === 'thumbnails' ? 'selected' : ''}`}
            onClick={() => setTargetStage('thumbnails')}
          >
            <div className="option-icon-box thumbnails">
              <Sparkles size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">Thumbnail Image</div>
              <div className="option-desc">
                High-contrast vertical chalkboard title card thumbnails (1080x1920) for YouTube Shorts.
              </div>
            </div>
            <div className="option-stage-pill">Stage F</div>
          </div>
        </div>
      </div>

      {/* STEP 2: Collect Script IDs */}
      <div className="mass-step-card">
        <div className="step-header-with-actions">
          <div className="step-badge-row">
            <span className="step-number">Step 2</span>
            <span className="step-heading">Collect Script IDs</span>
          </div>

          <div className="mode-tabs">
            <button
              className={`mode-tab ${collectionMode === 'text' ? 'active' : ''}`}
              onClick={() => setCollectionMode('text')}
            >
              Direct Paste / Input
            </button>
            <button
              className={`mode-tab ${collectionMode === 'csv' ? 'active' : ''}`}
              onClick={() => setCollectionMode('csv')}
            >
              Load from CSV
            </button>
            <button
              className={`mode-tab ${collectionMode === 'catalog' ? 'active' : ''}`}
              onClick={() => setCollectionMode('catalog')}
            >
              Presets & Filters
            </button>
          </div>
        </div>

        {/* Input Method A: Text Area */}
        {collectionMode === 'text' && (
          <div className="input-method-box">
            <textarea
              className="id-textarea"
              rows={4}
              placeholder="Paste IDs separated by commas, spaces, or lines (e.g. EE01, SR02, FE05, IG10)..."
              value={rawIdInput}
              onChange={(e) => setRawIdInput(e.target.value)}
            />
            <div className="textarea-footer">
              <span className="id-count-hint">
                {parsedRawIds.length} unique ID(s) typed/pasted
              </span>
              {rawIdInput && (
                <button className="btn btn-secondary btn-sm" onClick={handleClearAll}>
                  <Trash2 size={13} />
                  <span>Clear Input</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Input Method B: CSV Upload */}
        {collectionMode === 'csv' && (
          <div className="input-method-box csv-upload-box">
            <label className="csv-dropzone">
              <Upload size={32} className="text-blue-400" />
              <div className="dropzone-text">
                <strong>Click to select a CSV file</strong> or drag & drop here
              </div>
              <div className="dropzone-hint">
                Extracts the <code>ID</code> column automatically
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </label>

            {csvFileName && (
              <div className="loaded-file-pill">
                <FileSpreadsheet size={16} />
                <span>{csvFileName}</span>
                <span className="file-id-count">({parsedRawIds.length} IDs loaded)</span>
              </div>
            )}
          </div>
        )}

        {/* Input Method C: Catalog Presets */}
        {collectionMode === 'catalog' && (
          <div className="input-method-box presets-box">
            <div className="presets-label">
              <Filter size={16} />
              <span>Quick scenario presets:</span>
            </div>
            <div className="presets-buttons-row">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleLoadFromCatalog('images')}
                disabled={isValidating}
              >
                <ImageIcon size={14} />
                <span>All Pending Scene Images</span>
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleLoadFromCatalog('voice')}
                disabled={isValidating}
              >
                <Mic size={14} />
                <span>All Pending Voice Tracks</span>
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleLoadFromCatalog('thumbnails')}
                disabled={isValidating}
              >
                <Sparkles size={14} />
                <span>All Pending Thumbnails</span>
              </button>
            </div>
          </div>
        )}

        {/* Validated ID Chips Container */}
        {validatedItems.length > 0 && (
          <div className="chips-container-wrapper">
            <div className="chips-header">
              <div className="chips-counts">
                <span className="count-badge valid">
                  <CheckCircle2 size={14} />
                  {validIds.length} Valid
                </span>
                {invalidItems.length > 0 && (
                  <span className="count-badge invalid">
                    <AlertTriangle size={14} />
                    {invalidItems.length} Not Found
                  </span>
                )}
              </div>

              <div className="chips-actions">
                {invalidItems.length > 0 && (
                  <button className="btn btn-secondary btn-sm text-amber-400" onClick={handleRemoveInvalid}>
                    Remove {invalidItems.length} Invalid
                  </button>
                )}
                <button className="btn btn-secondary btn-sm" onClick={handleClearAll}>
                  Clear All
                </button>
              </div>
            </div>

            <div className="chips-grid">
              {validatedItems.map((item) => (
                <div
                  key={item.id}
                  className={`script-id-chip ${item.exists ? 'valid' : 'invalid'}`}
                  title={item.exists ? `${item.language || ''} ${item.type || ''}` : 'Script state does not exist in state/'}
                >
                  <span
                    className="chip-id-text"
                    onClick={() => item.exists && onSelectScript(item.id)}
                  >
                    {item.id}
                    {item.exists && <ExternalLink size={10} className="chip-link-icon" />}
                  </span>

                  {item.exists && item.language && (
                    <span className="chip-meta-tag">
                      {item.language}/{item.type}
                    </span>
                  )}

                  <button
                    className="chip-remove-btn"
                    onClick={() => handleRemoveId(item.id)}
                    title={`Remove ${item.id}`}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* STEP 3: Execution Settings & Launch */}
      <div className="mass-step-card">
        <div className="step-badge-row">
          <span className="step-number">Step 3</span>
          <span className="step-heading">Execution & Force Overwrite</span>
        </div>

        <div className="settings-content">
          <label className="checkbox-label highlight">
            <input
              type="checkbox"
              checked={forceRegenerate}
              onChange={(e) => setForceRegenerate(e.target.checked)}
            />
            <span className="checkbox-text">
              <strong>Force re-generate even if marked as "done" in state JSON</strong>
              <span className="checkbox-hint">
                Re-creates and overwrites existing asset files for all targeted IDs, resetting downstream status.
              </span>
            </span>
          </label>

          {/* ComfyUI Service Warning */}
          {isComfyRequired && !comfyOnline && (
            <div className="sheets-alert error">
              <AlertTriangle size={18} />
              <span>
                <strong>ComfyUI is currently offline.</strong> Please start ComfyUI using the toggle in the top navbar
                before launching generation for {targetStage}.
              </span>
            </div>
          )}

          <div className="launch-action-row">
            <button
              className="btn btn-primary btn-lg"
              disabled={validIds.length === 0 || isSubmitting}
              onClick={handleLaunch}
            >
              <Play size={18} />
              <span>
                {isSubmitting
                  ? 'Dispatching Job...'
                  : `Launch Mass Generation (${validIds.length} Scripts)`}
              </span>
            </button>
            <span className="launch-hint">
              Target: <strong className="capitalize">{targetStage}</strong> • {validIds.length} script(s) queued
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

