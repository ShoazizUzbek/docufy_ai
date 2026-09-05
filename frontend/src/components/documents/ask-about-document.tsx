"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ConversationTurnCard } from "@/components/ask-ai/conversation-turn";
import { askQuestion } from "@/lib/api/ask-ai";
import { ApiError } from "@/lib/api/client";
import { useOpenDocumentPassage } from "@/hooks/use-open-document-passage";
import type { AskAIAnswer, ConversationTurn } from "@/lib/api/types";

interface Turn {
  question: string;
  answer: AskAIAnswer;
}

export function AskAboutDocument({ documentId }: { documentId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const openDocumentPassage = useOpenDocumentPassage();

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
      const answer = await askQuestion(trimmed, history, documentId);
      setTurns((prev) => [...prev, { question: trimmed, answer }]);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to get an answer.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-xs font-medium tracking-wide text-tertiary-foreground uppercase">
        Ask about this document
      </h3>

      {turns.map((turn, i) => (
        <ConversationTurnCard
          key={i}
          question={turn.question}
          answer={turn.answer}
          onOpenSource={openDocumentPassage}
          onFollowUp={send}
        />
      ))}

      {isSending && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          disabled={isSending}
          className="h-9"
        />
        <Button type="submit" disabled={isSending || !input.trim()} size="icon" className="shrink-0">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
