"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { apiRequest } from "@/lib/api";

interface BatchStatusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  batchId: string | null;
}

interface BatchStatus {
  batch_id: string;
  project_name: string;
  status: string;
  current_file_index: number;
  total_files: number;
  files: Array<{
    filename: string;
    meeting_type: string;
  }>;
  file_statuses?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export default function BatchStatusDialog({
  open,
  onOpenChange,
  batchId,
}: BatchStatusDialogProps) {
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && batchId) {
      fetchBatchStatus();
      const interval = setInterval(fetchBatchStatus, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }
  }, [open, batchId]);

  const fetchBatchStatus = async () => {
    if (!batchId) return;
    
    setLoading(true);
    try {
      const data = await apiRequest(`/batch-status/${batchId}`);
      setBatchStatus(data);
    } catch (error) {
      console.error("Error fetching batch status:", error);
    } finally {
      setLoading(false);
    }
  };

  const getProgressPercentage = () => {
    if (!batchStatus) return 0;
    return (batchStatus.current_file_index / batchStatus.total_files) * 100;
  };

  const getFileStatus = (index: number) => {
    if (!batchStatus?.file_statuses) return "pending";
    return batchStatus.file_statuses[index.toString()] || "pending";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "text-green-600";
      case "processing": return "text-blue-600";
      case "uploaded": return "text-yellow-600";
      case "error": return "text-red-600";
      default: return "text-gray-600";
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Batch Upload Status</DialogTitle>
        </DialogHeader>
        
        {batchStatus ? (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Project: {batchStatus.project_name}</span>
                <span>Status: {batchStatus.status}</span>
              </div>
              <div className="flex justify-between text-sm mb-2">
                <span>Progress: {batchStatus.current_file_index} / {batchStatus.total_files}</span>
                <span>{Math.round(getProgressPercentage())}%</span>
              </div>
              <Progress value={getProgressPercentage()} className="h-2" />
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Files:</h4>
              {batchStatus.files.map((file, index) => (
                <div key={index} className="flex justify-between items-center text-sm p-2 border rounded">
                  <div>
                    <div className="font-medium">{file.filename}</div>
                    <div className="text-gray-500">{file.meeting_type}</div>
                  </div>
                  <span className={`font-medium ${getStatusColor(getFileStatus(index))}`}>
                    {getFileStatus(index)}
                  </span>
                </div>
              ))}
            </div>

            <div className="text-xs text-gray-500">
              Last updated: {new Date(batchStatus.updated_at).toLocaleString()}
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            {loading ? "Loading batch status..." : "No batch data available"}
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
