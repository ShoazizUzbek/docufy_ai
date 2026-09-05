export interface Organization {
  id: string;
  name: string;
  slug: string;
}

export type UserRole = "ADMIN" | "MEMBER";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization: Organization;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";

export type DocumentFileType = "PDF" | "DOCX" | "TXT" | "IMAGE";

export type DocumentCategory = "CONTRACT" | "REGULATION" | "POLICY" | "REPORT" | "OTHER" | "";

export interface DocumentEntities {
  dates?: string[];
  amounts?: string[];
  parties?: string[];
}

export interface Document {
  id: string;
  original_filename: string;
  file_type: DocumentFileType;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message: string;
  page_count: number | null;
  category: DocumentCategory;
  entities: DocumentEntities;
  uploaded_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  original_filename: string;
  page_number: number | null;
  section_heading: string;
  hierarchy_path: string;
  text: string;
  score: number;
}

export interface Source {
  index: number;
  chunk_id: string;
  document_id: string;
  original_filename: string;
  page_number: number | null;
  section_heading: string;
  hierarchy_path: string;
  text: string;
  score: number;
}

export interface ConversationTurn {
  question: string;
  answer: string;
}

export interface AskAIAnswer {
  answer: string;
  confident: boolean;
  citations: Source[];
  sources: Source[];
  follow_up_questions: string[];
}

export interface DocumentChunk {
  id: string;
  index: number;
  page_number: number | null;
  section_heading: string;
  hierarchy_path: string;
  text: string;
}

export interface DocumentPage {
  page_number: number | null;
  chunks: DocumentChunk[];
}
