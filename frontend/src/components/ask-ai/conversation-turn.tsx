"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { CitationChip } from "./citation-chip";
import type { AskAIAnswer, Source } from "@/lib/api/types";

interface ConversationTurnProps {
  question: string;
  answer: AskAIAnswer;
  onOpenSource: (source: Source) => void;
  onFollowUp: (question: string) => void;
}

export function ConversationTurnCard({ question, answer, onOpenSource, onFollowUp }: ConversationTurnProps) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm font-medium">{question}</p>

      <div
        className={cn(
          "rounded-lg border p-4",
          answer.confident ? "border-border bg-card" : "border-dashed border-border-strong bg-secondary/40"
        )}
      >
        <p className="font-serif text-[15px] leading-relaxed whitespace-pre-wrap">{answer.answer}</p>

        {answer.citations.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {answer.citations.map((citation) => (
              <CitationChip key={citation.chunk_id} source={citation} onClick={onOpenSource} />
            ))}
          </div>
        )}
      </div>

      {answer.sources.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowSources((prev) => !prev)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            {showSources ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {showSources ? "Hide" : "Show"} {answer.sources.length} source{answer.sources.length === 1 ? "" : "s"}
          </button>

          {showSources && (
            <div className="mt-2 flex flex-col gap-1.5">
              {answer.sources.map((source) => (
                <button
                  type="button"
                  key={source.chunk_id}
                  onClick={() => onOpenSource(source)}
                  className="flex items-center justify-between gap-2 rounded-md border border-border bg-card px-3 py-2 text-left text-xs transition-colors hover:border-border-strong"
                >
                  <span className="truncate text-muted-foreground">
                    [{source.index}] {source.original_filename}
                    {source.page_number != null ? ` · p.${source.page_number}` : ""}
                    {source.hierarchy_path ? ` · ${source.hierarchy_path}` : ""}
                  </span>
                  <span className="shrink-0 text-tertiary-foreground">{Math.round(source.score * 100)}%</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {answer.follow_up_questions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {answer.follow_up_questions.map((question) => (
            <button
              type="button"
              key={question}
              onClick={() => onFollowUp(question)}
              className="rounded-full border border-border bg-secondary/60 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
