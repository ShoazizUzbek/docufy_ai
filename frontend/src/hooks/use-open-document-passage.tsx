"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { DocumentPassageViewer } from "@/components/documents/document-passage-viewer";
import { useContextPanel } from "./use-context-panel";

interface PassageTarget {
  document_id: string;
  chunk_id: string;
  original_filename: string;
}

/** Opens the ContextPanel showing the full document, scrolled and
 * highlighted to one passage — what every citation click across the app
 * (Search, Ask AI, the Document Viewer) does. */
export function useOpenDocumentPassage() {
  const { open } = useContextPanel();

  return function openDocumentPassage(target: PassageTarget) {
    open(
      target.original_filename,
      <div className="flex flex-col gap-4">
        <Link
          href={`/documents/${target.document_id}`}
          className="flex w-fit items-center gap-1 text-xs text-primary hover:underline"
        >
          Open full document
          <ArrowUpRight className="h-3 w-3" />
        </Link>
        <DocumentPassageViewer documentId={target.document_id} targetChunkId={target.chunk_id} />
      </div>
    );
  };
}
