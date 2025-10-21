"use client";

import * as React from "react";
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from "@/components/ui/navigation-menu";
import { Input } from "./ui/input";
import { useState } from "react";
import Image from "next/image";
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
    <NavigationMenu viewport={false}>
      <NavigationMenuList className="bg-secondary w-screen flex justify-between p-3">
        <NavigationMenuLink
          href="/"
          className="font-bold text-md flex flex-row gap-2 items-center"
        >
          <Image src="/logo.png" alt="dxhub logo" width={35} height={35} />
          <NavigationMenuItem>AI-Powered Project Management</NavigationMenuItem>
        </NavigationMenuLink>
        <NavigationMenuItem>
          <Input
            // type="password"
            placeholder="api key"
            value={apiKey}
            onChange={(e) => handleSetApiKey(e.target.value)}
            className={
              apiKeyValid === ApiKeyState.valid
                ? "border-green-500"
                : apiKeyValid === ApiKeyState.invalid
                ? "border-red-500"
                : apiKeyValid === ApiKeyState.checking
                ? "border-yellow-500"
                : ""
            }
          />
        </NavigationMenuItem>
      </NavigationMenuList>
    </NavigationMenu>
  );
}
