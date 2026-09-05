"use client";

import { use, useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { CategoryBadge } from "@/components/documents/category-badge";
import { DocumentPassageViewer } from "@/components/documents/document-passage-viewer";
import { AskAboutDocument } from "@/components/documents/ask-about-document";
import { getDocument } from "@/lib/api/documents";
import { formatBytes, formatDateTime } from "@/lib/format";
import { useContextPanel } from "@/hooks/use-context-panel";
import type { Document } from "@/lib/api/types";

function EntityGroup({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {values.map((value) => (
          <span
            key={value}
            className="inline-flex items-center rounded-md border border-border bg-secondary px-2 py-0.5 text-xs text-foreground"
          >
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function ExtractedEntities({ document }: { document: Document }) {
  if (!document.category) {
    return (
      <p className="text-sm text-tertiary-foreground">
        {document.status === "READY"
          ? "No entities were extracted for this document."
          : "Entities will appear once processing finishes."}
      </p>
    );
  }

  const dates = document.entities.dates ?? [];
  const amounts = document.entities.amounts ?? [];
  const parties = document.entities.parties ?? [];

  if (dates.length === 0 && amounts.length === 0 && parties.length === 0) {
    return <p className="text-sm text-tertiary-foreground">No entities found in this document.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {parties.length > 0 && <EntityGroup label="Parties" values={parties} />}
      {dates.length > 0 && <EntityGroup label="Dates" values={dates} />}
      {amounts.length > 0 && <EntityGroup label="Amounts" values={amounts} />}
    </div>
  );
}

function DocumentMetadataPanel({ document }: { document: Document }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="mb-3 text-xs font-medium tracking-wide text-tertiary-foreground uppercase">
          Details
        </h3>
        <dl className="flex flex-col gap-2 text-sm">
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Status</dt>
            <dd>
              <DocumentStatusBadge status={document.status} />
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Category</dt>
            <dd>
              <CategoryBadge category={document.category} />
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Type</dt>
            <dd>{document.file_type}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Pages</dt>
            <dd>{document.page_count ?? "–"}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Size</dt>
            <dd>{formatBytes(document.file_size)}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Uploaded by</dt>
            <dd className="truncate">{document.uploaded_by_email ?? "–"}</dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-muted-foreground">Uploaded</dt>
            <dd>{formatDateTime(document.created_at)}</dd>
          </div>
        </dl>
      </div>

      <div>
        <h3 className="mb-3 text-xs font-medium tracking-wide text-tertiary-foreground uppercase">
          Extracted entities
        </h3>
        <ExtractedEntities document={document} />
      </div>

      {document.status === "READY" && (
        <div className="border-t border-border pt-6">
          <AskAboutDocument documentId={document.id} />
        </div>
      )}
    </div>
  );
}

export default function DocumentViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [document, setDocument] = useState<Document | null>(null);
  const [error, setError] = useState(false);
  const { open: openPanel } = useContextPanel();

  useEffect(() => {
    getDocument(id)
      .then(setDocument)
      .catch(() => setError(true));
  }, [id]);

  useEffect(() => {
    if (document) {
      openPanel(document.original_filename, <DocumentMetadataPanel document={document} />);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document]);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 py-20 text-center">
        <AlertCircle className="h-5 w-5 text-tertiary-foreground" />
        <p className="text-sm text-muted-foreground">Couldn&rsquo;t load this document.</p>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-medium">{document.original_filename}</h1>
        <p className="text-sm text-muted-foreground">
          {document.file_type} · {formatBytes(document.file_size)}
        </p>
      </div>

      {document.status === "READY" && <DocumentPassageViewer documentId={document.id} />}

      {document.status === "PROCESSING" && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          This document is still processing — check back shortly.
        </p>
      )}

      {document.status === "UPLOADED" && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          This document hasn&rsquo;t started processing yet.
        </p>
      )}

      {document.status === "FAILED" && (
        <div className="flex flex-col items-center gap-2 py-10 text-center">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-muted-foreground">Processing failed for this document.</p>
          {document.error_message && (
            <p className="max-w-md text-xs text-destructive">{document.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}
