"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiRequest } from "@/lib/api";

interface MeetingFile {
  file: File;
  filename: string;
  date: string;
  meeting_type: string;
  parsedDate?: string;
}

export default function BatchUpload() {
  const [projectId, setProjectId] = useState("");
  const [files, setFiles] = useState<MeetingFile[]>([]);
  const [uploading, setUploading] = useState(false);

  const parseDateFromFilename = (filename: string): string | null => {
    const pattern = /(\d{4}-\d{2}-\d{2})/;
    const match = filename.match(pattern);
    return match ? match[1] : null;
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    const validFiles = selectedFiles.filter(file => 
      file.name.endsWith('.txt') || file.name.endsWith('.vtt')
    );

    const meetingFiles: MeetingFile[] = validFiles.map(file => ({
      file,
      filename: file.name,
      date: parseDateFromFilename(file.name) || "",
      meeting_type: "",
      parsedDate: parseDateFromFilename(file.name) || undefined,
    }));

    setFiles(meetingFiles);
  };

  const updateMeeting = (index: number, field: keyof MeetingFile, value: string) => {
    const updatedFiles = [...files];
    updatedFiles[index] = { ...updatedFiles[index], [field]: value };
    setFiles(updatedFiles);
  };

  const moveMeeting = (fromIndex: number, toIndex: number) => {
    const updatedFiles = [...files];
    const [movedFile] = updatedFiles.splice(fromIndex, 1);
    updatedFiles.splice(toIndex, 0, movedFile);
    setFiles(updatedFiles);
  };

  const handleSubmit = async () => {
    if (!projectId || files.length === 0) {
      alert("Please provide project ID and select files");
      return;
    }

    // Validate all meetings have required fields
    for (const meeting of files) {
      if (!meeting.date || !meeting.meeting_type) {
        alert("Please fill in all date and meeting type fields");
        return;
      }
    }

    setUploading(true);
    try {
      // Upload files to S3 first (simplified - in real implementation, get presigned URLs)
      const meetings = files.map(meeting => ({
        filename: meeting.filename,
        date: meeting.date,
        meeting_type: meeting.meeting_type,
      }));

      const response = await apiRequest("/meetings-upload", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          meetings,
        }),
      });

      alert(`Successfully created ${response.meetings?.length || 0} meetings`);
      setFiles([]);
      setProjectId("");
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader>
          <CardTitle>Batch Meeting Upload</CardTitle>
          <p className="text-sm text-muted-foreground">
            Upload multiple meeting transcripts and organize them chronologically
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="text-sm font-medium">Project ID</label>
            <Input
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="Enter project name"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Select Files (.txt or .vtt)</label>
            <Input
              type="file"
              multiple
              accept=".txt,.vtt"
              onChange={handleFileSelect}
            />
          </div>

          {files.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-medium">Meeting Files (drag to reorder)</h3>
              {files.map((meeting, index) => (
                <Card key={index} className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                    <div>
                      <label className="text-xs text-muted-foreground">Filename</label>
                      <p className="text-sm font-medium">{meeting.filename}</p>
                      {meeting.parsedDate && (
                        <p className="text-xs text-green-600">
                          Parsed date: {meeting.parsedDate}
                        </p>
                      )}
                    </div>
                    
                    <div>
                      <label className="text-xs text-muted-foreground">Date (YYYY-MM-DD)</label>
                      <Input
                        type="date"
                        value={meeting.date}
                        onChange={(e) => updateMeeting(index, "date", e.target.value)}
                        required
                      />
                    </div>
                    
                    <div>
                      <label className="text-xs text-muted-foreground">Meeting Type</label>
                      <Select
                        value={meeting.meeting_type}
                        onValueChange={(value) => updateMeeting(index, "meeting_type", value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="discovery">Discovery</SelectItem>
                          <SelectItem value="demo">Demo</SelectItem>
                          <SelectItem value="executive-review">Executive Review</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => moveMeeting(index, Math.max(0, index - 1))}
                        disabled={index === 0}
                      >
                        ↑
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => moveMeeting(index, Math.min(files.length - 1, index + 1))}
                        disabled={index === files.length - 1}
                      >
                        ↓
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          <Button
            onClick={handleSubmit}
            disabled={uploading || files.length === 0 || !projectId}
            className="w-full"
          >
            {uploading ? "Uploading..." : `Upload ${files.length} Meetings`}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
