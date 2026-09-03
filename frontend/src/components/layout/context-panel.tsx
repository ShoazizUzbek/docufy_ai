"use client";

import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useContextPanel } from "@/hooks/use-context-panel";

export function ContextPanel() {
  const { isOpen, title, content, close } = useContextPanel();

  return (
    <aside
      className={cn(
        "hidden shrink-0 flex-col border-l border-border bg-card transition-[width] duration-150 lg:flex",
        isOpen ? "w-[420px]" : "w-0 overflow-hidden border-l-0"
      )}
    >
      {isOpen && (
        <>
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
            <h2 className="truncate text-sm font-medium">{title}</h2>
            <button
              type="button"
              onClick={close}
              className="rounded-md p-1 text-tertiary-foreground hover:bg-secondary hover:text-foreground"
              aria-label="Close panel"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">{content}</div>
        </>
      )}
    </aside>
  );
}
