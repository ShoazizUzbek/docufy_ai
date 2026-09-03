"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { ContextPanel } from "./context-panel";
import { ContextPanelProvider } from "@/hooks/use-context-panel";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <ContextPanelProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((prev) => !prev)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl px-4 py-8 md:px-8">{children}</div>
          </main>
        </div>
        <ContextPanel />
      </div>
    </ContextPanelProvider>
  );
}
