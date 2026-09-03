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

export interface Document {
  id: string;
  original_filename: string;
  file_type: DocumentFileType;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message: string;
  page_count: number | null;
  uploaded_by_email: string | null;
  created_at: string;
  updated_at: string;
}
