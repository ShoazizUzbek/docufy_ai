"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { FileText, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DocumentStatusBadge } from "@/components/documents/document-status-badge";
import { CategoryBadge } from "@/components/documents/category-badge";
import { listDocuments, uploadDocument } from "@/lib/api/documents";
import { ApiError } from "@/lib/api/client";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { Document } from "@/lib/api/types";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.txt,.png,.jpg,.jpeg,.tif,.tiff,.bmp";
const ACTIVE_STATUSES = new Set(["UPLOADED", "PROCESSING"]);

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[] | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to load documents.");
    }
  }, []);

  useEffect(() => {
    Promise.resolve().then(refresh);
  }, [refresh]);

  useEffect(() => {
    const hasActiveDocument = documents?.some((doc) => ACTIVE_STATUSES.has(doc.status));
    if (!hasActiveDocument) return;
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [documents, refresh]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    try {
      for (const file of Array.from(files)) {
        try {
          const document = await uploadDocument(file);
          setDocuments((prev) => (prev ? [document, ...prev] : [document]));
        } catch (err) {
          toast.error(
            err instanceof ApiError ? `${file.name}: ${err.message}` : `${file.name}: upload failed.`
          );
        }
      }
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-medium">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload contracts, policies, and reports for AI-powered search and Q&amp;A.
          </p>
        </div>
        <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
          <Upload className="h-4 w-4" />
          {isUploading ? "Uploading…" : "Upload"}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center transition-colors ${
          isDragOver ? "border-primary bg-accent/60" : "border-border-strong bg-secondary/40 hover:bg-secondary/60"
        }`}
      >
        <FileText className="h-6 w-6 text-tertiary-foreground" />
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Click to upload</span> or drag and drop
        </p>
        <p className="text-xs text-tertiary-foreground">PDF, DOCX, TXT, or scanned images</p>
      </div>

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Pages</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents === null &&
              Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}

            {documents !== null && documents.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  No documents yet. Upload your first document to get started.
                </TableCell>
              </TableRow>
            )}

            {documents?.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell className="max-w-xs truncate font-medium">
                  <Link href={`/documents/${doc.id}`} className="hover:underline">
                    {doc.original_filename}
                  </Link>
                </TableCell>
                <TableCell>
                  <DocumentStatusBadge status={doc.status} />
                  {doc.status === "FAILED" && doc.error_message && (
                    <p className="mt-1 max-w-xs truncate text-xs text-destructive">{doc.error_message}</p>
                  )}
                </TableCell>
                <TableCell>
                  <CategoryBadge category={doc.category} />
                </TableCell>
                <TableCell className="text-muted-foreground">{doc.file_type}</TableCell>
                <TableCell className="text-muted-foreground">{doc.page_count ?? "–"}</TableCell>
                <TableCell className="text-muted-foreground">{formatBytes(doc.file_size)}</TableCell>
                <TableCell className="text-muted-foreground">{formatDateTime(doc.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
