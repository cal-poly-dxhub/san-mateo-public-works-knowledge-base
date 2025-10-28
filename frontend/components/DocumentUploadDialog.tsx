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
import { Switch } from "@/components/ui/switch";
import { apiRequest } from "@/lib/api";

interface DocumentUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  projectType: string;
  onUploadComplete: () => void;
}

export default function DocumentUploadDialog({
  open,
  onOpenChange,
  projectName,
  projectType,
  onUploadComplete,
}: DocumentUploadDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [extractLessons, setExtractLessons] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    try {
      const content = await file.text();

      await apiRequest(
        `/projects/${encodeURIComponent(projectName)}/documents`,
        {
          method: "POST",
          body: JSON.stringify({
            filename: file.name,
            content: content,
            extract_lessons: extractLessons,
            project_type: projectType,
          }),
        },
      );

      alert(extractLessons ? "Document uploaded! Processing lessons..." : "Document uploaded!");
      onUploadComplete();
      onOpenChange(false);
      setFile(null);
      setExtractLessons(false);
    } catch (error) {
      console.error("Error uploading document:", error);
      alert("Error uploading document");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Document</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="file">Document File *</Label>
            <Input
              id="file"
              type="file"
              accept=".txt,.md,.pdf,.doc,.docx"
              onChange={handleFileChange}
              required
            />
            {file && (
              <span className="text-sm text-muted-foreground">
                Selected: {file.name}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="extract-lessons"
              checked={extractLessons}
              onCheckedChange={setExtractLessons}
            />
            <Label htmlFor="extract-lessons" className="cursor-pointer">
              Extract Lessons Learned
            </Label>
          </div>

          {extractLessons && (
            <div className="text-sm text-muted-foreground bg-muted p-3 rounded">
              AI will analyze this document and extract key lessons learned.
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !file}>
              {loading ? "Uploading..." : "Upload"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
