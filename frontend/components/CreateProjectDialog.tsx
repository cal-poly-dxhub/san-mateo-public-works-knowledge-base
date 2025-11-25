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
import { Switch } from "@/components/ui/switch";
import { useApi } from "@/lib/api-context";
import { apiRequest } from "@/lib/api";
import { XIcon } from "lucide-react";

interface FileWithToggle {
  file: File;
  extractLessons: boolean;
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
  const [projectName, setProjectName] = useState("");
  const [projectType, setProjectType] = useState("");
  const [projectTypes, setProjectTypes] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [areaSize, setAreaSize] = useState("");
  const [specialConditions, setSpecialConditions] = useState<string[]>([]);
  const [files, setFiles] = useState<FileWithToggle[]>([]);
  const [loading, setLoading] = useState(false);

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
    setFiles(prev => prev.map((f, i) => 
      i === index ? { ...f, extractLessons: !f.extractLessons } : f
    ));
  };

  const toggleAll = (checked: boolean) => {
    setFiles(prev => prev.map(f => ({ ...f, extractLessons: checked })));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Create project
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

      // Upload documents if any
      if (files.length > 0) {
        const uploadResponse = await apiRequest("/upload-url", {
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

        await Promise.all(
          uploadResponse.uploads.map(async (upload: any, index: number) => {
            const blob = new Blob([await files[index].file.arrayBuffer()]);
            await fetch(upload.uploadUrl, {
              method: "PUT",
              body: blob,
            });
          })
        );
      }

      onProjectCreated();
      onOpenChange(false);
      resetForm();
    } catch (error) {
      console.error("Error creating project:", error);
      alert("Error creating project");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setProjectName("");
    setProjectType(projectTypes[0] || "");
    setLocation("");
    setAreaSize("");
    setSpecialConditions([]);
    setFiles([]);
  };

  const allChecked = files.length > 0 && files.every(f => f.extractLessons);
  const someChecked = files.some(f => f.extractLessons) && !allChecked;

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
            <Label htmlFor="files">Upload Documents (Optional)</Label>
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

              <div className="space-y-2 max-h-[200px] overflow-y-auto">
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
