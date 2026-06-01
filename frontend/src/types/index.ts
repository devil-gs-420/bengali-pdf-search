// ─── Auth Types ───────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ─── Document Types ───────────────────────────────────────────────────────────

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: number;
  filename: string;
  file_size?: number;
  page_count?: number;
  status: DocumentStatus;
  error_message?: string;
  is_scanned: boolean;
  ocr_confidence?: number;
  records_extracted: number;
  processing_time_seconds?: number;
  folder_path?: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ─── Voter Record Types ───────────────────────────────────────────────────────

export interface VoterRecord {
  id: number;
  voter_id?: string;
  serial_number?: string;
  name?: string;
  name_english?: string;
  father_name?: string;
  mother_name?: string;
  spouse_name?: string;
  birth_date?: string;
  birth_year?: number;
  gender?: string;
  occupation?: string;
  address?: string;
  village?: string;
  post_office?: string;
  union_name?: string;
  ward?: string;
  upazila?: string;
  district?: string;
  division?: string;
  document_id: number;
  page_number?: number;
  extraction_confidence?: number;
  pdf_file_name?: string;
}

export interface VoterRecordListResponse {
  items: VoterRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  query?: string;
  search_duration_ms?: number;
}

// ─── Search Types ─────────────────────────────────────────────────────────────

export interface SearchFilters {
  query?: string;
  name?: string;
  father_name?: string;
  mother_name?: string;
  voter_id?: string;
  birth_date?: string;
  district?: string;
  upazila?: string;
  union_name?: string;
  ward?: string;
  occupation?: string;
  village?: string;
  gender?: string;
  birth_year_from?: number;
  birth_year_to?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ─── Upload Types ─────────────────────────────────────────────────────────────

export interface UploadSession {
  session_id: string;
  total_files: number;
  status: string;
  message: string;
}

export interface UploadProgress {
  session_id: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  total_records: number;
  status: string;
  progress_percent: number;
  error_details?: string[];
}

// ─── Stats Types ──────────────────────────────────────────────────────────────

export interface SystemStats {
  total_documents: number;
  total_records: number;
  failed_documents: number;
  processing_documents: number;
  pending_documents: number;
  completed_documents: number;
  total_searches: number;
  recent_uploads: number;
  storage_used_mb: number;
  top_districts: { district: string; count: number }[];
  recent_activity: {
    session_id: string;
    folder_name?: string;
    total_files: number;
    processed_files: number;
    total_records: number;
    status: string;
    started_at?: string;
  }[];
}

// ─── Export Types ─────────────────────────────────────────────────────────────

export type ExportFormat = 'csv' | 'excel' | 'json';

export interface ExportRequest {
  format: ExportFormat;
  query?: string;
  filters?: Record<string, string>;
  fields?: string[];
  max_records?: number;
}
