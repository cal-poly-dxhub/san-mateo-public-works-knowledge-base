"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api";

interface FileUpload {
  file: File;
  document_type: string;
  date: string;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  progress: number;
}

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onProjectCreated: (batchId?: string) => void;
}

export default function CreateProjectDialog({
  open,
  onOpenChange,
  onProjectCreated,
}: CreateProjectDialogProps) {
  const { apiKey } = useApiKey();
  const [projectName, setProjectName] = useState("");
  const [projectType, setProjectType] = useState("");
  const [projectTypes, setProjectTypes] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [areaSize, setAreaSize] = useState("");
  const [specialConditions, setSpecialConditions] = useState<string[]>([]);
  const [files, setFiles] = useState<FileUpload[]>([]);
  const [loading, setLoading] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);

  useEffect(() => {
    const loadProjectTypes = async () => {
      try {
        const data = await apiRequest("/config/project-types");
        setProjectTypes(data.project_types || []);
        if (data.project_types?.length > 0) {
          setProjectType(data.project_types[0]);
        }
      } catch (error) {
        console.error("Error loading project types:", error);
      }
    };
    loadProjectTypes();
  }, []);



  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles = selectedFiles.map(file => {
      // Extract date from filename using regex (YYYY-MM-DD format)
      const dateMatch = file.name.match(/(\d{4}-\d{2}-\d{2})/);
      const extractedDate = dateMatch ? dateMatch[1] : '';
      
      return {
        file,
        document_type: '',
        date: extractedDate,
        status: 'pending' as const,
        progress: 0,
      };
    });
    setFiles(prev => [...prev, ...newFiles]);
  };

  const updateFileDocumentType = (index: number, document_type: string) => {
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, document_type } : f
    ));
  };

  const updateFileDate = (index: number, date: string) => {
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, date } : f
    ));
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Create project using wizard
      await apiRequest("/create-project", {
        method: "POST",
        body: JSON.stringify({
          projectName: projectName,
          projectType: projectType,
          location: location,
          areaSize: areaSize,
          specialConditions: specialConditions,
        }),
      });

      // If files are selected, start batch upload
      if (files.length > 0) {
        const resultBatchId = await startBatchUpload();
        onProjectCreated(resultBatchId);
      } else {
        onProjectCreated();
      }
      onOpenChange(false);
      resetForm();
    } catch (error) {
      console.error("Error creating project:", error);
      alert("Error creating project");
    } finally {
      setLoading(false);
    }
  };

  const startBatchUpload = async (): Promise<string> => {
    // Read file contents
    const fileData = await Promise.all(files.map(async (f) => {
      const content = await f.file.text(); // Read file content as text
      return {
        filename: f.file.name,
        document_type: f.document_type || 'general',
        date: f.date,
        content: content, // Include file content
      };
    }));

    // Create documents with content
    const response = await apiRequest("/document-upload", {
      method: "POST",
      body: JSON.dumps({
        project_id: projectName,
        documents: fileData,
      }),
    });

    // The document upload API creates document records and uploads files
    return response.documents?.[0]?.uuid || 'batch-created';
  };

  const resetForm = () => {
    setProjectName("");
    setProjectType(projectTypes[0] || "");
    setLocation("");
    setAreaSize("");
    setSpecialConditions([]);
    setFiles([]);
    setBatchId(null);
  };



  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="projectName">Project Name *</Label>
            <Input
              id="projectName"
              value={projectName}
              onChange={(e) => {
                const value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-');
                setProjectName(value);
              }}
              placeholder="highway-1-slurry-seal"
              pattern="[a-z0-9\-]+"
              title="Only lowercase letters, numbers, and hyphens allowed"
              required
            />
            <span className="text-xs text-muted-foreground">Use lowercase letters, numbers, and hyphens only</span>
          </div>
          
          <div className="flex flex-col gap-2">
            <Label htmlFor="projectType">Project Type *</Label>
            <select
              id="projectType"
              value={projectType}
              onChange={(e) => setProjectType(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            >
              {projectTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="location">Location *</Label>
            <Input
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., Main St between 1st and 5th Ave"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="areaSize">Work Area Size (acres) *</Label>
            <Input
              id="areaSize"
              type="number"
              step="0.1"
              value={areaSize}
              onChange={(e) => setAreaSize(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="specialConditions">Special Conditions</Label>
            <Textarea
              id="specialConditions"
              placeholder="e.g., Near school zone, High traffic area, Utility conflicts (comma-separated)"
              onChange={(e) => setSpecialConditions(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
              rows={2}
            />
          </div>
          
          <div className="flex flex-col gap-2">
            <Label htmlFor="files">Upload Project Documents (Optional)</Label>
            <Input
              id="files"
              type="file"
              multiple
              accept="video/*,audio/*,.txt,.vtt"
              onChange={handleFileChange}
              className="hover:cursor-pointer"
            />
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              <Label>Selected Files</Label>
              {files.map((fileUpload, index) => (
                <div key={index} className="border rounded p-3 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{fileUpload.file.name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                    >
                      Remove
                    </Button>
                  </div>
                  <Input
                    placeholder="Document type (e.g., lessons learned, project plan, report)"
                    value={fileUpload.document_type}
                    onChange={(e) => updateFileDocumentType(index, e.target.value)}
                  />
                  <Input
                    type="date"
                    value={fileUpload.date}
                    onChange={(e) => updateFileDate(index, e.target.value)}
                  />
                  {fileUpload.status !== 'pending' && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>Status: {fileUpload.status}</span>
                        <span>{fileUpload.progress}%</span>
                      </div>
                      <Progress value={fileUpload.progress} className="h-2" />
                    </div>
                  )}
                </div>
              ))}
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
            <Button type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Project"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
