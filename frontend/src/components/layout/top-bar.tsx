"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { searchChunks } from "@/lib/api/search";
import type { SearchResult } from "@/lib/api/types";

const DEBOUNCE_MS = 300;

export function TopBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
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

  useEffect(() => {
    if (!query.trim()) {
      Promise.resolve().then(() => {
        setResults([]);
        setIsSearching(false);
      });
      return;
    }
    Promise.resolve().then(() => setIsSearching(true));
    const timeout = setTimeout(() => {
      searchChunks(query, 5)
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setIsSearching(false));
    }, DEBOUNCE_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  function goToSearchPage() {
    setOpen(false);
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

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

      <CommandDialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setQuery("");
        }}
        title="Global search"
        description="Search documents or jump to a page"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search documents, ask a question…"
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {query.trim() && (
              <CommandGroup heading="Results">
                {isSearching && results.length === 0 && (
                  <div className="px-2 py-3 text-sm text-muted-foreground">Searching…</div>
                )}
                {!isSearching && results.length === 0 && (
                  <CommandEmpty>No matching passages found.</CommandEmpty>
                )}
                {results.map((result) => (
                  <CommandItem
                    key={result.chunk_id}
                    value={result.chunk_id}
                    onSelect={goToSearchPage}
                    className="flex flex-col items-start gap-0.5"
                  >
                    <span className="w-full truncate text-sm font-medium">{result.original_filename}</span>
                    {(result.hierarchy_path || result.page_number) && (
                      <span className="text-xs text-tertiary-foreground">
                        {result.hierarchy_path}
                        {result.hierarchy_path && result.page_number ? " · " : ""}
                        {result.page_number ? `Page ${result.page_number}` : ""}
                      </span>
                    )}
                    <span className="w-full truncate text-xs text-muted-foreground">{result.text}</span>
                  </CommandItem>
                ))}
                {results.length > 0 && (
                  <CommandItem value="__view_all" onSelect={goToSearchPage} className="text-primary">
                    View all results for &ldquo;{query}&rdquo;
                  </CommandItem>
                )}
              </CommandGroup>
            )}

            {query.trim() && <CommandSeparator />}

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
        </Command>
      </CommandDialog>
    </header>
  );
}
