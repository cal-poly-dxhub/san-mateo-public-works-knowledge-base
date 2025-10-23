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
        <Link href="/" className="font-bold text-md flex flex-row gap-2 items-center">
          <Image src="/logo.png" alt="dxhub logo" width={35} height={35} />
          AI-Powered Project Management
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm hover:underline hover:text-primary transition-colors">
            Dashboard
          </Link>
          <Link href="/lessons-learned" className="text-sm hover:underline hover:text-primary transition-colors">
            Lessons Learned
          </Link>
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
