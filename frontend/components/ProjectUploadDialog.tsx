"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiRequest } from "@/lib/api";

interface ProjectUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  onUploadComplete?: () => void;
}

export default function ProjectUploadDialog({
  open,
  onOpenChange,
  projectName,
  onUploadComplete,
}: ProjectUploadDialogProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [meetingType, setMeetingType] = useState<string>("general");
  const [meetingDate, setMeetingDate] = useState<string>("");

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      
      // Auto-extract date from filename
      const dateMatch = file.name.match(/(\d{4}-\d{2}-\d{2})/);
      if (dateMatch) {
        setMeetingDate(dateMatch[1]);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !meetingDate) {
      alert("Please select a file and enter a meeting date");
      return;
    }

    setLoading(true);
    try {
      // Read file content
      const content = await selectedFile.text();
      
      // Use batch upload API
      await apiRequest("/batch-upload", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectName,
          meetings: [{
            filename: selectedFile.name,
            meeting_type: meetingType,
            date: meetingDate,
            content: content,
          }],
        }),
      });

      alert("File uploaded successfully!");
      onOpenChange(false);
      setSelectedFile(null);
      setMeetingDate("");
      setMeetingType("general");
      onUploadComplete?.();
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Meeting File to {projectName}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label htmlFor="file">Select File (.txt or .vtt)</Label>
            <Input
              id="file"
              type="file"
              accept=".txt,.vtt"
              onChange={handleFileChange}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="date">Meeting Date</Label>
            <Input
              id="date"
              type="date"
              value={meetingDate}
              onChange={(e) => setMeetingDate(e.target.value)}
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="type">Meeting Type</Label>
            <Select value={meetingType} onValueChange={setMeetingType}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="Select meeting type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General</SelectItem>
                <SelectItem value="standup">Standup</SelectItem>
                <SelectItem value="planning">Planning</SelectItem>
                <SelectItem value="review">Review</SelectItem>
                <SelectItem value="retrospective">Retrospective</SelectItem>
                <SelectItem value="demo">Demo</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex justify-end space-x-2">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button onClick={handleUpload} disabled={loading || !selectedFile}>
              {loading ? "Uploading..." : "Upload"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
