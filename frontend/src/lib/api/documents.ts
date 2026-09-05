import { apiRequest } from "./client";
import type { Document, DocumentPage } from "./types";

export function listDocuments(): Promise<Document[]> {
  return apiRequest<Document[]>("/api/documents/");
}

export function getDocument(id: string): Promise<Document> {
  return apiRequest<Document>(`/api/documents/${id}/`);
}

export function getDocumentContent(id: string): Promise<DocumentPage[]> {
  return apiRequest<DocumentPage[]>(`/api/documents/${id}/content/`);
}

export function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<Document>("/api/documents/", {
    method: "POST",
    body: formData,
    isFormData: true,
  });
}
