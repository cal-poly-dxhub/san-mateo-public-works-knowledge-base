"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiRequest } from "@/lib/api";

interface AddLessonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  projectType: string;
  onComplete: () => void;
}

export default function AddLessonDialog({
  open,
  onOpenChange,
  projectName,
  projectType,
  onComplete,
}: AddLessonDialogProps) {
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) return;

    setLoading(true);
    try {
      const contentWithPrompt = `INSTRUCTION: This is a note from a user. Generate only ONE lesson learned based on this note.\n\n${notes}`;
      
      await apiRequest(
        `/projects/${encodeURIComponent(projectName)}/documents`,
        {
          method: "POST",
          body: JSON.stringify({
            filename: `lesson-${Date.now()}.txt`,
            content: contentWithPrompt,
            extract_lessons: true,
            project_type: projectType,
          }),
        },
      );

      alert("Lesson submitted! Processing in background...");
      onComplete();
      onOpenChange(false);
      setNotes("");
    } catch (error) {
      console.error("Error adding lesson:", error);
      alert("Error adding lesson");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Lesson Learned</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="notes">Lesson Notes *</Label>
            <Textarea
              id="notes"
              placeholder="What did you learn? What would you do differently next time?"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={6}
              required
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !notes.trim()}>
              {loading ? "Submitting..." : "Add Lesson"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
