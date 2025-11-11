"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { X, Upload, FileText } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface FileWithLessons {
  file: File;
  extractLessons: boolean;
}

interface InitialDocumentUploadProps {
  projectId: string;
  projectType?: string;
  onUploadComplete?: () => void;
}

export default function InitialDocumentUpload({
  projectId,
  projectType,
  onUploadComplete,
}: InitialDocumentUploadProps) {
  const [files, setFiles] = useState<FileWithLessons[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles: File[]) => {
    const validFiles = newFiles.filter((file) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      return ["txt", "pdf", "doc", "docx"].includes(ext || "");
    });

    const filesWithLessons = validFiles.map((file) => ({
      file,
      extractLessons: false,
    }));

    setFiles((prev) => [...prev, ...filesWithLessons]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const toggleLessons = (index: number) => {
    setFiles((prev) =>
      prev.map((f, i) =>
        i === index ? { ...f, extractLessons: !f.extractLessons } : f
      )
    );
  };

  const extractText = async (file: File): Promise<string> => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext === "txt") {
      return await file.text();
    }
    // For PDF/DOC, return base64 for backend processing
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsDataURL(file);
    });
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    try {
      for (const { file, extractLessons } of files) {
        // Get presigned URL
        const { uploadUrl } = await apiRequest("/upload-url", {
          method: "POST",
          body: JSON.stringify({
            fileName: file.name,
            projectId: projectId,
          }),
        });

        // Upload file to S3
        await fetch(uploadUrl, {
          method: "PUT",
          body: file,
          headers: {
            "Content-Type": file.type || "application/octet-stream",
          },
        });

        // If lessons learned is enabled, trigger the workflow
        if (extractLessons) {
          const content = await extractText(file);
          await apiRequest(`/projects/${encodeURIComponent(projectId)}/documents`, {
            method: "POST",
            body: JSON.stringify({
              filename: file.name,
              content: content,
              extract_lessons: true,
              project_type: projectType || "general",
            }),
          });
        }
      }

      alert(`Successfully uploaded ${files.length} file(s)`);
      setFiles([]);
      onUploadComplete?.();
    } catch (error) {
      console.error("Upload error:", error);
      alert("Error uploading files. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? "border-primary bg-primary/5"
            : "border-gray-300 hover:border-gray-400"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <p className="text-sm text-gray-600 mb-2">
          Drag and drop files here, or click to select
        </p>
        <p className="text-xs text-gray-500 mb-4">
          Supports: TXT, PDF, DOC, DOCX
        </p>
        <input
          type="file"
          multiple
          accept=".txt,.pdf,.doc,.docx"
          onChange={handleFileInput}
          className="hidden"
          id="file-upload"
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => document.getElementById("file-upload")?.click()}
        >
          Select Files
        </Button>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            Files to Upload ({files.length})
          </Label>
          {files.map((fileItem, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3 flex-1">
                <FileText className="h-5 w-5 text-gray-500" />
                <span className="text-sm truncate">{fileItem.file.name}</span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={fileItem.extractLessons}
                    onCheckedChange={() => toggleLessons(index)}
                    id={`lessons-${index}`}
                  />
                  <Label
                    htmlFor={`lessons-${index}`}
                    className="text-xs cursor-pointer whitespace-nowrap"
                  >
                    Lessons Learned
                  </Label>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
          <Button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full mt-4"
          >
            {uploading ? "Uploading..." : `Upload ${files.length} File(s)`}
          </Button>
        </div>
      )}
    </div>
  );
}
