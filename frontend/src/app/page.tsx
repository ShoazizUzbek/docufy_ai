"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? "/documents" : "/login");
  }, [isLoading, user, router]);

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background text-sm text-muted-foreground">
      Loading…
    </div>
  );
}
