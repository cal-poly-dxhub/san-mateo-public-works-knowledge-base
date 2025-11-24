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
import { XIcon } from "lucide-react";

interface FileWithToggle {
  file: File;
  extractLessons: boolean;
}

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
  const [files, setFiles] = useState<FileWithToggle[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, boolean>>({});

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map(file => ({
        file,
        extractLessons: false
      }));
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const toggleFile = (index: number) => {
    const file = files[index].file;
    const newExtractLessons = !files[index].extractLessons;
    
    // Check file size limit for lesson extraction (256KB)
    if (newExtractLessons && file.size > 256 * 1024) {
      alert(`${file.name} is too large for lesson extraction (max 256KB). Upload without lesson extraction or use a smaller file.`);
      return;
    }
    
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, extractLessons: newExtractLessons } : f
    ));
  };

  const toggleAll = (checked: boolean) => {
    // Check if any files exceed 256KB limit
    if (checked) {
      const oversizedFiles = files.filter(f => f.file.size > 256 * 1024);
      if (oversizedFiles.length > 0) {
        alert(`${oversizedFiles.length} file(s) exceed 256KB limit for lesson extraction. They will be skipped.`);
        setFiles(prev => prev.map(f => ({ 
          ...f, 
          extractLessons: f.file.size <= 256 * 1024 
        })));
        return;
      }
    }
    setFiles(prev => prev.map(f => ({ ...f, extractLessons: checked })));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setLoading(true);
    setUploadProgress({});

    try {
      // Request presigned URLs for all files
      const response = await apiRequest("/upload-url", {
        method: "POST",
        body: JSON.stringify({
          files: files.map(({ file, extractLessons }) => ({
            fileName: file.name,
            projectName: projectName,
            projectType: projectType,
            extractLessons: extractLessons,
          })),
        }),
      });

      const uploads = response.uploads || [];

      // Upload all files in parallel
      await Promise.all(
        uploads.map(async (upload: any, index: number) => {
          const file = files[index].file;
          await fetch(upload.uploadUrl, {
            method: "PUT",
            body: file,
          });
          setUploadProgress(prev => ({ ...prev, [file.name]: true }));
        })
      );

      alert(files.length === 1 ? "Document uploaded!" : "All documents uploaded!");
      onUploadComplete();
      onOpenChange(false);
      setFiles([]);
      setUploadProgress({});
    } catch (error) {
      console.error("Error uploading documents:", error);
      alert("Error uploading documents");
    } finally {
      setLoading(false);
    }
  };

  const allChecked = files.length > 0 && files.every(f => f.extractLessons);
  const someChecked = files.some(f => f.extractLessons) && !allChecked;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="files">Select Documents *</Label>
            <Input
              id="files"
              type="file"
              accept=".txt,.md,.pdf,.doc,.docx"
              onChange={handleFileChange}
              multiple
            />
          </div>

          {files.length > 0 && (
            <>
              <div className="flex items-center justify-between p-3 bg-muted rounded">
                <Label htmlFor="toggle-all" className="cursor-pointer font-semibold">
                  Extract Lessons for All
                </Label>
                <Switch
                  id="toggle-all"
                  checked={allChecked}
                  onCheckedChange={toggleAll}
                  className={someChecked ? "opacity-50" : ""}
                />
              </div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {files.map((fileItem, index) => (
                  <div
                    key={`${fileItem.file.name}-${index}`}
                    className="flex items-center justify-between p-3 border rounded"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {fileItem.file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(fileItem.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-3 ml-4">
                      {uploadProgress[fileItem.file.name] && (
                        <span className="text-xs text-green-600">✓</span>
                      )}
                      <div className="flex items-center gap-2">
                        <Label
                          htmlFor={`extract-${index}`}
                          className="text-xs cursor-pointer whitespace-nowrap"
                        >
                          Lessons
                        </Label>
                        <Switch
                          id={`extract-${index}`}
                          checked={fileItem.extractLessons}
                          onCheckedChange={() => toggleFile(index)}
                          disabled={loading}
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        disabled={loading}
                      >
                        <XIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || files.length === 0}>
              {loading ? `Uploading ${Object.keys(uploadProgress).length}/${files.length}...` : `Upload ${files.length} Document${files.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
