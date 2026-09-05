import type { DocumentCategory } from "@/lib/api/types";

const CATEGORY_LABELS: Record<Exclude<DocumentCategory, "">, string> = {
  CONTRACT: "Contract",
  REGULATION: "Regulation",
  POLICY: "Policy",
  REPORT: "Report",
  OTHER: "Other",
};

export function CategoryBadge({ category }: { category: DocumentCategory }) {
  if (!category) {
    return <span className="text-tertiary-foreground">–</span>;
  }

  return (
    <span className="inline-flex items-center rounded-full border border-border-strong bg-secondary px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
      {CATEGORY_LABELS[category]}
    </span>
  );
}
