"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

export function TopBar() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4 md:px-6">
      <div />
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex w-full max-w-sm items-center gap-2 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-sm text-tertiary-foreground transition-colors hover:border-border-strong hover:text-muted-foreground"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">Search documents, ask a question…</span>
        <kbd className="rounded border border-border-strong bg-background px-1.5 py-0.5 text-[10px] font-medium text-tertiary-foreground">
          &#8984;K
        </kbd>
      </button>
      <div />

      <CommandDialog open={open} onOpenChange={setOpen} title="Global search" description="Search documents or jump to a page">
        <CommandInput placeholder="Search documents, ask a question…" />
        <CommandList>
          <CommandEmpty>Semantic search arrives in Phase 3.</CommandEmpty>
          <CommandGroup heading="Go to">
            <CommandItem onSelect={() => { setOpen(false); router.push("/documents"); }}>
              Documents
            </CommandItem>
            <CommandItem onSelect={() => { setOpen(false); router.push("/ask-ai"); }}>
              Ask AI
            </CommandItem>
            <CommandItem onSelect={() => { setOpen(false); router.push("/search"); }}>
              Search
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </header>
  );
}
