import { Sparkles } from "lucide-react";

export function ComingSoon({
  title,
  phase,
  description,
}: {
  title: string;
  phase: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border-strong px-6 py-16 text-center">
      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent text-accent-foreground">
        <Sparkles className="h-4 w-4" />
      </span>
      <h1 className="text-base font-medium">{title}</h1>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      <p className="text-xs text-tertiary-foreground">Coming in {phase}.</p>
    </div>
  );
}
