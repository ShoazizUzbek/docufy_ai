import { cn } from "@/lib/utils";
import type { DocumentStatus } from "@/lib/api/types";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  UPLOADED: "bg-secondary text-muted-foreground border-border-strong",
  PROCESSING: "bg-accent text-accent-foreground border-accent-foreground/20",
  READY: "bg-accent text-accent-foreground border-accent-foreground/20",
  FAILED: "bg-destructive/10 text-destructive border-destructive/30",
};

const STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: "Uploaded",
  PROCESSING: "Processing",
  READY: "Ready",
  FAILED: "Failed",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        STATUS_STYLES[status]
      )}
    >
      {status === "PROCESSING" && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {STATUS_LABELS[status]}
    </span>
  );
}
