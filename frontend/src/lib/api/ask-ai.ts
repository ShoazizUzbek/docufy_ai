import { apiRequest } from "./client";
import type { AskAIAnswer, ConversationTurn } from "./types";

export function askQuestion(
  question: string,
  conversationHistory: ConversationTurn[] = [],
  documentId?: string
): Promise<AskAIAnswer> {
  return apiRequest<AskAIAnswer>("/api/ask/", {
    method: "POST",
    body: { question, conversation_history: conversationHistory, document_id: documentId ?? null },
  });
}
