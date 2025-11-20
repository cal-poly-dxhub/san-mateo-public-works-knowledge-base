"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { apiRequest } from "@/lib/api";

export default function KBSyncButton() {
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  const handleSync = async () => {
    setSyncing(true);
    setMessage("");

    try {
      const response = await apiRequest("/sync/knowledge-base", {
        method: "POST",
      });

      const data = await response.json();

      if (response.status === 200) {
        setMessage("✓ Sync started successfully");
      } else if (response.status === 409) {
        const stats = data.currentJob?.statistics || {};
        const statsText = stats.numberOfDocumentsScanned 
          ? ` (${stats.numberOfDocumentsScanned} docs scanned)`
          : "";
        setMessage(`⏳ Sync already in progress${statsText}`);
      } else {
        setMessage(`✗ ${data.error || "Sync failed"}`);
      }
    } catch (error) {
      setMessage(`✗ Error: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setSyncing(false);
      setTimeout(() => setMessage(""), 5000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button
        onClick={handleSync}
        disabled={syncing}
        variant="outline"
        size="sm"
      >
        <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
        Sync Knowledge Base
      </Button>
      {message && (
        <span className="text-sm text-muted-foreground">{message}</span>
      )}
    </div>
  );
}
