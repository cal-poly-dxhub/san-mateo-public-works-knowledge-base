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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Project {
  name: string;
}

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function UploadDialog({
  open,
  onOpenChange,
}: UploadDialogProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [meetingType, setMeetingType] = useState<string>("");

  useEffect(() => {
    if (open) {
      loadProjects();
    }
  }, [open]);

  const loadProjects = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}projects`, {
        headers: {
          'x-api-key': process.env.NEXT_PUBLIC_API_KEY!
        }
      });
      const projectsData = await response.json();
      setProjects(projectsData);
    } catch (error) {
      console.error("Error loading projects:", error);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setSelectedFile(file || null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !selectedProject || !meetingType) return;

    setLoading(true);

    try {
      // Get pre-signed URL for upload
      const uploadResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}upload-url`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'x-api-key': process.env.NEXT_PUBLIC_API_KEY!
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          project_name: selectedProject,
          meeting_type: meetingType
        })
      });

      const { upload_url, fields } = await uploadResponse.json();

      // Upload file to S3
      const formData = new FormData();
      Object.keys(fields).forEach(key => {
        formData.append(key, fields[key]);
      });
      formData.append('file', selectedFile);

      const uploadResult = await fetch(upload_url, {
        method: 'POST',
        body: formData
      });

      if (uploadResult.ok) {
        onOpenChange(false);
        setSelectedFile(null);
        setSelectedProject("");
        setMeetingType("");
        alert("Video uploaded successfully! Processing will begin shortly.");
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error("Error uploading video:", error);
      alert("Error uploading video");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Meeting File</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="projectSelect" className="mb-3">
              Select Project
            </Label>
            <Select value={selectedProject} onValueChange={setSelectedProject} required>
              <SelectTrigger>
                <SelectValue placeholder="Choose a project..." />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.name} value={project.name}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="meetingType" className="mb-3">
              Meeting Type
            </Label>
            <Input
              id="meetingType"
              type="text"
              placeholder="e.g., standup, planning, review, discovery"
              value={meetingType}
              onChange={(e) => setMeetingType(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="videoFile" className="mb-3">
              Select Meeting File
            </Label>
            <Input
              id="videoFile"
              type="file"
              accept="video/*,audio/*,.txt,.vtt"
              onChange={handleFileChange}
              required
              className="hover:cursor-pointer"
            />
          </div>
          {selectedFile && (
            <div className="text-sm text-muted-foreground">
              Selected: {selectedFile.name} (
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
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
            <Button type="submit" disabled={!selectedFile || !selectedProject || !meetingType || loading}>
              {loading ? "Uploading..." : "Upload File"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
