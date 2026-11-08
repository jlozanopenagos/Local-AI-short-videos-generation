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
  music: StageState
  thumbnails: StageState
  assembly: StageState
}

export interface ScriptAssets {
  audio: string | null
  images: string[]
  thumbnail: string | null
  video: string | null
}

export interface ScriptSummary {
  script_id: string
  topic: string
  language: string
  type: string
  character: {
    gender: string
    description: string
  }
  stages: ScriptStages
  assets: ScriptAssets
}

export interface SceneDetail {
  scene_type: string
  voice_line: string
  image_file: string | null
  prompt?: string
}

export interface ScriptDetail extends ScriptSummary {
  story_scenario?: string
  lexical_field?: string
  base_setting?: string
  scenes?: SceneDetail[]
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

