"use client";

import * as React from "react";
import { Input } from "./ui/input";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
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
    const stored = sessionStorage.getItem('checklist-type') as "design" | "construction";
    if (stored) {
      setChecklistType(stored);
    }
    setMounted(true);
  }, []);

  const handleToggle = (checked: boolean) => {
    const newType = checked ? "construction" : "design";
    setChecklistType(newType);
    sessionStorage.setItem('checklist-type', newType);
    window.dispatchEvent(new CustomEvent('checklistTypeChange', { detail: newType }));
  };

  if (!mounted) {
    return (
      <div className="flex items-center gap-2">
        <Label className="text-xs text-secondary-foreground">Design</Label>
        <Switch disabled />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Label className="text-xs text-secondary-foreground">Design</Label>
      <Switch
        checked={checklistType === "construction"}
        onCheckedChange={handleToggle}
        className="data-[state=checked]:bg-green-500"
      />
      <Label className="text-xs text-secondary-foreground">Construction</Label>
    </div>
  );
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
          <Link href="/upload" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Upload
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
