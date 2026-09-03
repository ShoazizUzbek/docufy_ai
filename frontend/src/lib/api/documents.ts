import { apiRequest } from "./client";
import type { Document } from "./types";

export function listDocuments(): Promise<Document[]> {
  return apiRequest<Document[]>("/api/documents/");
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
