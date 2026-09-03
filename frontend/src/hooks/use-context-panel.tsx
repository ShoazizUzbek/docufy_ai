"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

interface ContextPanelState {
  isOpen: boolean;
  title: string | null;
  content: React.ReactNode | null;
}

interface ContextPanelValue extends ContextPanelState {
  open: (title: string, content: React.ReactNode) => void;
  close: () => void;
}

const ContextPanelContext = createContext<ContextPanelValue | null>(null);

export function ContextPanelProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ContextPanelState>({
    isOpen: false,
    title: null,
    content: null,
  });

  const open = useCallback((title: string, content: React.ReactNode) => {
    setState({ isOpen: true, title, content });
  }, []);

  const close = useCallback(() => {
    setState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const value = useMemo(() => ({ ...state, open, close }), [state, open, close]);

  return <ContextPanelContext.Provider value={value}>{children}</ContextPanelContext.Provider>;
}

export function useContextPanel(): ContextPanelValue {
  const ctx = useContext(ContextPanelContext);
  if (!ctx) throw new Error("useContextPanel must be used within a ContextPanelProvider");
  return ctx;
}
