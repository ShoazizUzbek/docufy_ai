"use client";

import { useEffect, useRef, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { getDocumentContent } from "@/lib/api/documents";
import { cn } from "@/lib/utils";
import type { DocumentPage } from "@/lib/api/types";

interface DocumentPassageViewerProps {
  documentId: string;
  /** When set, that chunk is highlighted and scrolled into view. */
  targetChunkId?: string;
}

export function DocumentPassageViewer({ documentId, targetChunkId }: DocumentPassageViewerProps) {
  const [pages, setPages] = useState<DocumentPage[] | null>(null);
  const [error, setError] = useState(false);
  const targetRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    Promise.resolve().then(() => {
      setPages(null);
      setError(false);
    });
    getDocumentContent(documentId)
      .then(setPages)
      .catch(() => setError(true));
  }, [documentId]);

  useEffect(() => {
    if (pages && targetRef.current) {
      targetRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [pages]);

  if (error) {
    return <p className="text-sm text-muted-foreground">Couldn&rsquo;t load this document&rsquo;s content.</p>;
  }

  if (!pages) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (pages.length === 0) {
    return <p className="text-sm text-muted-foreground">This document has no processed content yet.</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      {pages.map((page) => (
        <div key={page.page_number ?? "unknown"}>
          {page.page_number != null && (
            <p className="mb-2 text-xs font-medium text-tertiary-foreground">Page {page.page_number}</p>
          )}
          <div className="flex flex-col gap-4">
            {page.chunks.map((chunk) => (
              <p
                key={chunk.id}
                ref={chunk.id === targetChunkId ? targetRef : undefined}
                className={cn(
                  "-mx-2 rounded px-2 py-1 font-serif text-[15px] leading-relaxed whitespace-pre-wrap",
                  chunk.id === targetChunkId && "bg-accent"
                )}
              >
                {chunk.text}
              </p>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
