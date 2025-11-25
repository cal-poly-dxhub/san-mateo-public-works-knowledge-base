"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { apiRequest, apiRequestRaw } from "@/lib/api";

interface SyncStatus {
  status: string;
  jobId?: string;
  statistics?: {
    documentsScanned: number;
    documentsModified: number;
    documentsFailed: number;
  };
  message?: string;
}

export default function KBSyncButton() {
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState<SyncStatus | null>(null);
  const pollInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    checkStatus();
    
    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current);
      }
    };
  }, []);

  const checkStatus = async () => {
    try {
      const data: SyncStatus = await apiRequest("/sync/knowledge-base/status", {
        method: "GET",
      });
      
      if (data.status === "in_progress" || data.status === "starting") {
        setProgress(data);
        setSyncing(true);
        startPolling();
      } else if (data.status === "complete") {
        setProgress(data);
        setMessage(data.message || "Sync complete");
        setSyncing(false);
        stopPolling();
      } else {
        setSyncing(false);
        stopPolling();
      }
    } catch (error) {
      console.error("Error checking sync status:", error);
    }
  };

  const startPolling = () => {
    if (pollInterval.current) return;
    
    pollInterval.current = setInterval(async () => {
      await checkStatus();
    }, 3000);
  };

  const stopPolling = () => {
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setMessage("");
    setProgress(null);

    try {
      const response = await apiRequestRaw("/sync/knowledge-base", {
        method: "POST",
      });

      const data = await response.json();

      if (response.status === 200) {
        setMessage("✓ Sync started");
        startPolling();
      } else if (response.status === 409) {
        setProgress(data);
        setMessage("⏳ Sync already in progress");
        startPolling();
      } else {
        setMessage(`✗ ${data.error || "Sync failed"}`);
        setSyncing(false);
      }
    } catch (error) {
      setMessage(`✗ Error: ${error instanceof Error ? error.message : "Unknown error"}`);
      setSyncing(false);
    }
  };

  const getProgressText = () => {
    if (!progress?.statistics) return "";
    
    const { documentsScanned, documentsModified, documentsFailed } = progress.statistics;
    
    if (progress.status === "complete") {
      return `${documentsModified} docs indexed`;
    }
    
    return `${documentsScanned} docs scanned${documentsFailed > 0 ? `, ${documentsFailed} failed` : ""}`;
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
      {syncing && (
        <span className="flex items-center gap-1 text-sm text-blue-600">
          <span className="inline-block w-2 h-2 bg-blue-600 rounded-full animate-pulse"></span>
          Sync in progress
        </span>
      )}
      {!syncing && progress?.status === "complete" && (
        <span className="flex items-center gap-1 text-sm text-green-600">
          <span className="inline-block w-2 h-2 bg-green-600 rounded-full"></span>
          Sync complete
        </span>
      )}
      {message && (
        <span className="text-sm text-muted-foreground">
          {progress && ` (${getProgressText()})`}
        </span>
      )}
    </div>
  );
}
