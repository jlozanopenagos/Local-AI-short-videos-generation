import type { SystemStatus, ScriptSummary, ScriptDetail, Job, JobStage, ScriptCatalogResponse, ScriptFacets, SheetsSyncStatus, ValidateIdsResponse } from './types'

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch('/api/system/status')
  if (!res.ok) throw new Error(`Status HTTP ${res.status}`)
  return res.json()
}

export async function controlService(
  service: 'comfyui' | 'llm',
  action: 'start' | 'stop' | 'restart'
): Promise<{ status: string; message: string }> {
  const res = await fetch(`/api/system/service/${service}/${action}`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Action ${action} failed`)
  }
  return res.json()
}

export interface CatalogQueryOptions {
  page?: number
  pageSize?: number
  search?: string
  language?: string
  videoType?: string
  stageFilter?: string
}

export async function fetchScriptCatalog(options: CatalogQueryOptions = {}): Promise<ScriptCatalogResponse> {
  const params = new URLSearchParams()
  params.set('page', String(options.page || 1))
  params.set('page_size', String(options.pageSize || 24))

  if (options.search) params.set('search', options.search)
  if (options.language && options.language !== 'all') params.set('language', options.language)
  if (options.videoType && options.videoType !== 'all') params.set('video_type', options.videoType)
  if (options.stageFilter && options.stageFilter !== 'all') params.set('stage_filter', options.stageFilter)

  const res = await fetch(`/api/scripts?${params.toString()}`)
  if (!res.ok) throw new Error(`Catalog HTTP ${res.status}`)
  return res.json()
}

export async function fetchFacets(): Promise<ScriptFacets> {
  const res = await fetch('/api/scripts/facets')
  if (!res.ok) throw new Error(`Facets HTTP ${res.status}`)
  return res.json()
}

export async function refreshScriptCache(): Promise<{ total_indexed: number }> {
  const res = await fetch('/api/scripts/refresh', { method: 'POST' })
  if (!res.ok) throw new Error(`Refresh HTTP ${res.status}`)
  return res.json()
}

export async function fetchScripts(): Promise<ScriptSummary[]> {
  const res = await fetch('/api/scripts')
  if (!res.ok) throw new Error(`Scripts HTTP ${res.status}`)
  return res.json()
}

export async function fetchScriptDetail(scriptId: string): Promise<ScriptDetail> {
  const res = await fetch(`/api/scripts/${scriptId}`)
  if (!res.ok) throw new Error(`Script HTTP ${res.status}`)
  return res.json()
}

export interface ScriptUpdatePayload {
  script_text?: string
  script_dict?: Record<string, any>
  chalkboard_exercise?: string
  chalkboard_title?: string
  target_expression?: string
  general_prompt?: string
  image_prompts?: Record<string, string>
}

export async function updateScript(scriptId: string, payload: ScriptUpdatePayload): Promise<ScriptDetail> {
  const res = await fetch(`/api/scripts/${scriptId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to update script ${scriptId}`)
  }
  return res.json()
}

export async function geminiAuditPrompt(
  scriptId: string,
  currentPrompt?: string,
  apiKey?: string
): Promise<{ status: string; audited_prompt: string; character_anchors?: Record<string, any>; script_id: string }> {
  const res = await fetch(`/api/scripts/${scriptId}/gemini-audit-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_prompt: currentPrompt,
      api_key: apiKey,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Gemini audit failed for script ${scriptId}`)
  }
  return res.json()
}

export async function generateScript(
  scriptId: string,
  options: { force?: boolean } = { force: true }
): Promise<{ status: string; job_id: string; script_id: string }> {
  const res = await fetch(`/api/scripts/${scriptId}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: options.force ?? true }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to trigger script generation for ${scriptId}`)
  }
  return res.json()
}

export async function renderChalkboard(
  scriptId: string,
  chalkboardExercise?: string
): Promise<{ status: string; message: string; image_file: string; script: ScriptDetail }> {
  const res = await fetch(`/api/scripts/${scriptId}/render-chalkboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chalkboard_exercise: chalkboardExercise,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to render chalkboard for script ${scriptId}`)
  }
  return res.json()
}

export async function toggleScriptStage(
  scriptId: string,
  stage: string,
  newStatus?: string
): Promise<{ script_id: string; stage: string; status_key: string; new_status: string; summary: ScriptSummary }> {
  const res = await fetch(`/api/scripts/${scriptId}/toggle-stage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stage, new_status: newStatus }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to toggle stage ${stage} for script ${scriptId}`)
  }
  return res.json()
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch('/api/jobs')
  if (!res.ok) throw new Error(`Jobs HTTP ${res.status}`)
  return res.json()
}

export async function createJob(stage: JobStage, scriptIds: string[], options: Record<string, unknown> = {}): Promise<Job> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      stage,
      script_ids: scriptIds,
      options,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to create job`)
  }
  return res.json()
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to cancel job`)
  }
}

export async function fetchGeminiStatus(): Promise<{ configured: boolean; model: string }> {
  const res = await fetch('/api/system/gemini-status')
  if (!res.ok) throw new Error(`Gemini status HTTP ${res.status}`)
  return res.json()
}

export async function saveGeminiKey(apiKey: string): Promise<{ status: string; message: string }> {
  const res = await fetch('/api/system/gemini-key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to save Gemini API key')
  }
  return res.json()
}

export function getMediaUrl(pathOrFilename?: string | null): string {
  if (!pathOrFilename) return ''
  if (pathOrFilename.startsWith('http://') || pathOrFilename.startsWith('https://')) {
    return pathOrFilename
  }
  return `/api/media?file=${encodeURIComponent(pathOrFilename)}`
}

export async function fetchSheetsSyncStatus(): Promise<SheetsSyncStatus> {
  const res = await fetch('/api/sheets/status')
  if (!res.ok) throw new Error(`Sheets status HTTP ${res.status}`)
  return res.json()
}

export async function startSheetsSync(options: { clean_cache?: boolean; apply_changes?: boolean } = {}): Promise<{ status: string; message: string }> {
  const res = await fetch('/api/sheets/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      clean_cache: options.clean_cache ?? true,
      apply_changes: options.apply_changes ?? true,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to start Google Sheets sync')
  }
  return res.json()
}

export async function resetSheetsSyncStatus(): Promise<{ status: string; message: string }> {
  const res = await fetch('/api/sheets/reset', { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to reset Sheets sync status')
  }
  return res.json()
}

export async function validateScriptIds(scriptIds: string[]): Promise<ValidateIdsResponse> {
  const res = await fetch('/api/scripts/validate-ids', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script_ids: scriptIds }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to validate script IDs')
  }
  return res.json()
}

export async function redoSceneImage(
  scriptId: string,
  sceneType: string,
  options: { prompt?: string; seed?: number } = {}
): Promise<{ status: string; message: string; image_file: string; script: ScriptDetail }> {
  const res = await fetch(`/api/scripts/${scriptId}/scenes/${encodeURIComponent(sceneType)}/redo-image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to redo image for scene '${sceneType}' in script ${scriptId}`)
  }
  return res.json()
}


