export interface ServiceStatus {
  status: 'online' | 'offline'
  pid: number | null
  port: number
}

export interface ComfyUIStatus extends ServiceStatus {
  active_gpu?: string
  vram_usage_gb?: number
  vram_total_gb?: number
  vram_free_gb?: number
  queue_running?: number
  queue_pending?: number
}

export interface LLMStatus extends ServiceStatus {
  model?: string
}

export interface SystemStatus {
  status: 'online' | 'offline'
  comfyui: ComfyUIStatus
  llm: LLMStatus
  platform: {
    os: string
    python: string
  }
}

export type StageState = 'done' | 'pending' | 'missing'

export interface ScriptStages {
  scripts: StageState
  voice: StageState
  images: StageState
  thumbnails: StageState
  assembly: StageState
}

export interface ScriptAssets {
  audio: string | null
  images: string[]
  thumbnail: string | null
  video: string | null
  poster?: string | null
}

export interface ScriptSummary {
  id: string
  script_id: string
  topic: string
  title?: string
  language: string
  type: string
  video_type: string
  lexical_field?: string
  scenario?: string
  character: {
    gender: string
    description: string
  }
  stages: ScriptStages
  assets: ScriptAssets
  has_voice: boolean
  has_images: boolean
  has_video: boolean
  has_thumbnail: boolean
  is_ready_for_assembly: boolean
}

export interface FacetItem {
  name: string
  count: number
}

export interface ScriptFacets {
  total: number
  languages: FacetItem[]
  types: FacetItem[]
  stage_counts: {
    all: number
    missing_voice: number
    missing_images: number
    ready_for_assembly: number
    complete: number
  }
}

export interface ScriptCatalogResponse {
  items: ScriptSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
  facets: ScriptFacets
}

export interface SceneDetail {
  scene_type: string
  label?: string
  voice_line: string
  image_file: string | null
  prompt?: string
}

export interface YouTubeMetadata {
  title: string
  description: string
  short_description?: string
  tags: string
  hashtags: string
  filename: string
  label?: string
}

export interface ScriptDetail extends ScriptSummary {
  story_scenario?: string
  base_setting?: string
  lexical_field?: string
  general_prompt?: string
  learning_objective?: string
  speakers_voice?: Record<string, string>
  speakers_gender?: Record<string, string>
  scenes?: SceneDetail[]
  youtube_metadata?: YouTubeMetadata
  script_text?: string
  script_dict?: Record<string, any>
  chalkboard_exercise?: string
  chalkboard_title?: string
  target_expression?: string
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

export type JobStage = 'scripts' | 'voice' | 'images' | 'music' | 'thumbnails' | 'assembly'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface JobProgress {
  current: number
  total: number
  current_script: string | null
  stage_label: string
}

export interface Job {
  job_id: string
  stage: JobStage
  status: JobStatus
  script_ids: string[]
  progress: JobProgress
  logs: string[]
  error?: string | null
  created_at: number
  started_at?: number | null
  finished_at?: number | null
}
