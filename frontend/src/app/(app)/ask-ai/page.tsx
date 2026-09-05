"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationTurnCard } from "@/components/ask-ai/conversation-turn";
import { askQuestion } from "@/lib/api/ask-ai";
import { ApiError } from "@/lib/api/client";
import { useOpenDocumentPassage } from "@/hooks/use-open-document-passage";
import type { AskAIAnswer, ConversationTurn, Source } from "@/lib/api/types";

interface Turn {
  question: string;
  answer: AskAIAnswer;
}

export default function AskAiPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const openDocumentPassage = useOpenDocumentPassage();
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || isSending) return;

    setInput("");
    setIsSending(true);

    const history: ConversationTurn[] = turns.map((turn) => ({
      question: turn.question,
      answer: turn.answer.answer,
    }));

    try {
      const answer = await askQuestion(trimmed, history);
      setTurns((prev) => [...prev, { question: trimmed, answer }]);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to get an answer.");
    } finally {
      setIsSending(false);
      requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));
    }
  }

  function openSource(source: Source) {
    openDocumentPassage(source);
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-lg font-medium">Ask AI</h1>
        <p className="text-sm text-muted-foreground">
          Ask a question — answers come only from your organization&rsquo;s documents, with citations.
        </p>
      </div>

      {turns.length === 0 && !isSending && (
        <p className="py-10 text-center text-sm text-muted-foreground">
          Ask anything about your documents to get started.
        </p>
      )}

      <div className="flex flex-col gap-8">
        {turns.map((turn, i) => (
          <ConversationTurnCard
            key={i}
            question={turn.question}
            answer={turn.answer}
            onOpenSource={openSource}
            onFollowUp={send}
          />
        ))}

        {isSending && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
      </div>

      <div ref={bottomRef} />

      <div className="sticky bottom-0 -mx-4 border-t border-border bg-background px-4 py-4 md:-mx-8 md:px-8">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-3xl items-center gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents…"
            disabled={isSending}
            className="h-10"
          />
          <Button type="submit" disabled={isSending || !input.trim()} size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
