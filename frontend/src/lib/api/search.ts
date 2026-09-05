import { apiRequest } from "./client";
import type { SearchResult } from "./types";

export function searchChunks(query: string, limit = 10): Promise<SearchResult[]> {
  return apiRequest<SearchResult[]>("/api/search/", {
    method: "POST",
    body: { query, limit },
  });
}
