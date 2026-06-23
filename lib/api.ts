const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type JobStatus =
  | "pending"
  | "downloading"
  | "compressing"
  | "scene_detection"
  | "transcribing"
  | "extracting_frames"
  | "ocr"
  | "embedding"
  | "indexing"
  | "completed"
  | "failed";

export interface SubmitResponse {
  job_id: string;
  video_id: string;
  status: JobStatus;
}

export interface JobStatusResponse {
  job_id: string;
  video_id: string;
  url: string;
  status: JobStatus;
  progress: number;
  message: string;
  error?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  id: string;
  text: string;
  timestamp_start: number;
  timestamp_end: number;
  modality: string;
  scene_id?: number;
  frame_path?: string;
  confidence?: number;
  rerank_score?: number;
}

export interface AskResponse {
  answer: string;
  confidence: string;
  evidence: EvidenceItem[];
  insufficient_evidence: boolean;
}

export interface VideoSummary {
  video_id: string;
  url: string;
  title?: string;
  status: JobStatus;
  chunk_count: number;
  created_at: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export function submitVideo(url: string) {
  return request<SubmitResponse>("/api/videos/submit", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function getJobStatus(jobId: string) {
  return request<JobStatusResponse>(`/api/videos/jobs/${jobId}`);
}

export function getVideoStatus(videoId: string) {
  return request<JobStatusResponse>(`/api/videos/status/${videoId}`);
}

export function listVideos() {
  return request<VideoSummary[]>("/api/videos");
}

export function askQuestion(videoId: string, question: string) {
  return request<AskResponse>(`/api/videos/${videoId}/ask`, {
    method: "POST",
    body: JSON.stringify({ video_id: videoId, question }),
  });
}

export function frameUrl(videoId: string, filename: string) {
  return `${API_BASE}/api/videos/${videoId}/frames/${filename}`;
}

export function videoUrl(videoId: string) {
  return `${API_BASE}/api/videos/${videoId}/video`;
}
