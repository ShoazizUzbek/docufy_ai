"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronsUpDown,
  FileText,
  LayoutGrid,
  MessagesSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sparkles,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NAV_ITEMS = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/ask-ai", label: "Ask AI", icon: Sparkles },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/analytics", label: "Analytics", icon: LayoutGrid },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside
      className={cn(
        "hidden md:flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-150",
        collapsed ? "w-[64px]" : "w-[248px]"
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-3">
        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/60",
              collapsed && "justify-center px-0"
            )}
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground">
              {user?.organization.name?.[0]?.toUpperCase() ?? "D"}
            </span>
            {!collapsed && (
              <>
                <span className="min-w-0 flex-1 truncate">
                  {user?.organization.name ?? "Docufy"}
                </span>
                <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-tertiary-foreground" />
              </>
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-56">
            <DropdownMenuLabel className="truncate text-xs text-muted-foreground">
              {user?.email}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={logout}>Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <button
          type="button"
          onClick={onToggle}
          className="hidden shrink-0 rounded-md p-1.5 text-tertiary-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground md:flex"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex flex-col gap-0.5 px-2 py-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                isActive && "bg-sidebar-accent font-medium text-sidebar-accent-foreground hover:bg-sidebar-accent",
                collapsed && "justify-center px-0"
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="mt-2 flex-1 overflow-y-auto px-2">
          <div className="flex items-center justify-between px-2.5 py-1.5">
            <span className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-tertiary-foreground">
              <MessagesSquare className="h-3.5 w-3.5" />
              Knowledge Spaces
            </span>
          </div>
          <p className="px-2.5 py-1 text-xs text-tertiary-foreground">No spaces yet</p>
        </div>
      )}
    </aside>
  );
}
