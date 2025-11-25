"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/api";

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<Record<string, boolean>>({});

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const handleUpload = async () => {
    setUploading(true);
    setProgress({});

    try {
      const response = await apiRequest("/upload-url", {
        method: "POST",
        body: JSON.stringify({
          files: files.map(file => ({
            fileName: file.name,
            extractLessons: false,
          })),
        }),
      });

      await Promise.all(
        response.uploads.map(async (upload: any, index: number) => {
          try {
            await fetch(upload.uploadUrl, {
              method: "PUT",
              body: files[index],
            });
            setProgress(prev => ({ ...prev, [files[index].name]: true }));
          } catch (error) {
            console.error(`Error uploading ${files[index].name}:`, error);
            setProgress(prev => ({ ...prev, [files[index].name]: false }));
          }
        })
      );

      alert("Upload complete!");
    } catch (error) {
      console.error("Error uploading files:", error);
      alert("Error uploading files");
    } finally {
      setUploading(false);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setFiles([]);
    setProgress({});
  };

  return (
    <div className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">General File Upload</h1>
      
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center mb-6 hover:border-gray-400 transition-colors"
      >
        <p className="text-lg mb-4">Drag and drop files here</p>
        <p className="text-sm text-gray-500 mb-4">or</p>
        <input
          id="file-input"
          type="file"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <label htmlFor="file-input">
          <Button type="button" variant="outline" asChild>
            <span>Browse Files</span>
          </Button>
        </label>
      </div>

      {files.length > 0 && (
        <>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">{files.length} files selected</h2>
            <div className="space-x-2">
              <Button onClick={clearAll} variant="outline" disabled={uploading}>
                Clear All
              </Button>
              <Button onClick={handleUpload} disabled={uploading || files.length === 0}>
                {uploading ? `Uploading ${Object.keys(progress).length}/${files.length}...` : "Upload All"}
              </Button>
            </div>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {files.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 border rounded"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {progress[file.name] === true && (
                    <span className="text-green-600 text-sm">✓</span>
                  )}
                  {progress[file.name] === false && (
                    <span className="text-red-600 text-sm">✗</span>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                    disabled={uploading}
                  >
                    ✕
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
