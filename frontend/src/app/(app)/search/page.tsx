"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search as SearchIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { searchChunks } from "@/lib/api/search";
import { ApiError } from "@/lib/api/client";
import { useOpenDocumentPassage } from "@/hooks/use-open-document-passage";
import type { SearchResult } from "@/lib/api/types";

const DEBOUNCE_MS = 400;

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const openDocumentPassage = useOpenDocumentPassage();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const trimmed = query.trim();

    const url = trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search";
    const timeout = setTimeout(() => router.replace(url), DEBOUNCE_MS);

    if (!trimmed) {
      Promise.resolve().then(() => {
        setResults(null);
        setError(null);
        setIsSearching(false);
      });
      return () => clearTimeout(timeout);
    }

    Promise.resolve().then(() => {
      setIsSearching(true);
      setError(null);
    });
    const searchTimeout = setTimeout(() => {
      searchChunks(trimmed, 20)
        .then(setResults)
        .catch((err) => setError(err instanceof ApiError ? err.message : "Search failed."))
        .finally(() => setIsSearching(false));
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timeout);
      clearTimeout(searchTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-medium">Search</h1>
        <p className="text-sm text-muted-foreground">
          Ask in plain language — search understands meaning, not just keywords.
        </p>
      </div>

      <div className="relative">
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-tertiary-foreground" />
        <Input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents, ask a question…"
          className="h-10 pl-9"
        />
      </div>

      {!query.trim() && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          Start typing to search across your organization&rsquo;s documents.
        </p>
      )}

      {query.trim() && isSearching && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {query.trim() && !isSearching && error && (
        <p className="py-10 text-center text-sm text-destructive">{error}</p>
      )}

      {query.trim() && !isSearching && !error && results?.length === 0 && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          No matching passages found. Try rephrasing your question.
        </p>
      )}

      {query.trim() && !isSearching && !error && results && results.length > 0 && (
        <div className="flex flex-col gap-3">
          {results.map((result) => (
            <button
              key={result.chunk_id}
              onClick={() => openDocumentPassage(result)}
              className="flex flex-col gap-1.5 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-border-strong"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium">{result.original_filename}</span>
                <span className="shrink-0 text-xs text-tertiary-foreground">
                  {Math.round(result.score * 100)}% match
                </span>
              </div>
              {(result.hierarchy_path || result.page_number) && (
                <span className="text-xs text-tertiary-foreground">
                  {result.hierarchy_path}
                  {result.hierarchy_path && result.page_number ? " · " : ""}
                  {result.page_number ? `Page ${result.page_number}` : ""}
                </span>
              )}
              <p className="line-clamp-3 text-sm text-muted-foreground">{result.text}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchPageContent />
    </Suspense>
  );
}
