"use client";

import * as React from "react";
import { Input } from "./ui/input";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useApiKey } from "@/lib/api-context";

enum ApiKeyState {
  empty,
  checking,
  valid,
  invalid,
}

function ChecklistToggle() {
  const [checklistType, setChecklistType] = useState<"design" | "construction">("design");
  const [mounted, setMounted] = useState(false);
  
  React.useEffect(() => {
    setMounted(true);
    // Get initial value from localStorage only on client
    const stored = localStorage.getItem('checklistType') as "design" | "construction";
    if (stored) {
      setChecklistType(stored);
    } else {
      // Set default and store it
      localStorage.setItem('checklistType', 'design');
    }
  }, []);

  React.useEffect(() => {
    if (!mounted) return;
    // Store in localStorage and dispatch event for other components
    localStorage.setItem('checklistType', checklistType);
    window.dispatchEvent(new CustomEvent('checklistTypeChange', { detail: checklistType }));
  }, [checklistType, mounted]);

  if (!mounted) {
    return (
      <select className="h-8 px-2 rounded-md border border-input bg-background text-xs text-secondary-foreground">
        <option>Design</option>
      </select>
    );
  }

  return (
    <select
      value={checklistType}
      onChange={(e) => setChecklistType(e.target.value as "design" | "construction")}
      className="h-8 px-2 rounded-md border border-input bg-background text-xs text-secondary-foreground"
    >
      <option value="design">Design</option>
      <option value="construction">Construction</option>
    </select>
  );
}

enum ApiKeyState {
  empty,
  checking,
  valid,
  invalid,
}

export default function Header() {
  const { apiKey, setApiKey, triggerRefresh } = useApiKey();
  const [apiKeyValid, setApiKeyValid] = useState<ApiKeyState>(
    ApiKeyState.empty
  );

  function handleSetApiKey(s: string) {
    setApiKey(s);
    if (s === "") {
      setApiKeyValid(ApiKeyState.empty);
      return;
    }
    setApiKeyValid(ApiKeyState.checking);
    triggerRefresh();
  }

  return (
    <nav className="bg-secondary w-full p-3 flex justify-between items-center">
      <div className="flex items-center gap-8">
        <Link href="/" className="font-bold text-md flex flex-row gap-2 items-center text-secondary-foreground">
          <Image src="/logo.png" alt="dxhub logo" width={35} height={35} />
          AI-Powered Project Management
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Dashboard
          </Link>
          <Link href="/lessons-learned" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Lessons Learned
          </Link>
          <Link href="/global-checklist" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Global Checklist
          </Link>
          <ChecklistToggle />
        </div>
      </div>
      <Input
        placeholder="api key"
        value={apiKey}
        onChange={(e) => handleSetApiKey(e.target.value)}
        className={`w-48 ${
          apiKeyValid === ApiKeyState.valid
            ? "border-green-500"
            : apiKeyValid === ApiKeyState.invalid
            ? "border-red-500"
            : apiKeyValid === ApiKeyState.checking
            ? "border-yellow-500"
            : ""
        }`}
      />
    </nav>
  );
}
