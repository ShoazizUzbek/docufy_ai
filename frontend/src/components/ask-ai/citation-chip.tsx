import type { Source } from "@/lib/api/types";

interface CitationChipProps {
  source: Source;
  onClick: (source: Source) => void;
}

export function CitationChip({ source, onClick }: CitationChipProps) {
  return (
    <button
      type="button"
      onClick={() => onClick(source)}
      className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground transition-colors hover:border-primary/50"
    >
      <span className="font-semibold">[{source.index}]</span>
      <span className="max-w-[160px] truncate">{source.original_filename}</span>
      {source.page_number != null && <span className="text-accent-foreground/70">p.{source.page_number}</span>}
    </button>
  );
}
