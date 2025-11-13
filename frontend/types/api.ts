export interface SearchResult {
  content: string;
  metadata: Record<string, any>;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  model_id: string;
}

export interface BatchStatus {
  batch_id: string;
  project_name: string;
  status: string;
  current_file_index: number;
  total_files: number;
  files: Array<{
    filename: string;
    meeting_type: string;
  }>;
  file_statuses?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ApiError {
  error: string;
  details?: string;
}
