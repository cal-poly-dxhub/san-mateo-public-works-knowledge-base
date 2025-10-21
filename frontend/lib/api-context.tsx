"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface ApiContextType {
  apiKey: string;
  setApiKey: (key: string) => void;
  refreshTrigger: number;
  triggerRefresh: () => void;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export function ApiProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem("apiKey") || process.env.NEXT_PUBLIC_API_KEY || "";
    }
    return process.env.NEXT_PUBLIC_API_KEY || "";
  });
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const triggerRefresh = () => setRefreshTrigger(prev => prev + 1);

  const setApiKey = (key: string) => {
    setApiKeyState(key);
    if (typeof window !== 'undefined') {
      localStorage.setItem("apiKey", key);
    }
    triggerRefresh();
  };

  return (
    <ApiContext.Provider value={{ apiKey, setApiKey, refreshTrigger, triggerRefresh }}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApiKey() {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error("useApiKey must be used within ApiProvider");
  }
  return context;
}
