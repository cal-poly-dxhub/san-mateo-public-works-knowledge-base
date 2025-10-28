"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle } from "lucide-react";

interface Lesson {
  title: string;
  lesson: string;
  impact: string;
  recommendation: string;
  severity: string;
}

interface LessonReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stats: {
    project_added: number;
    project_deleted: number;
    project_new_lessons: Lesson[];
    project_superseded_lessons: Lesson[];
  } | null;
}

export default function LessonReviewDialog({
  open,
  onOpenChange,
  stats,
}: LessonReviewDialogProps) {
  if (!stats) return null;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "High": return "bg-red-100 text-red-800";
      case "Medium": return "bg-yellow-100 text-yellow-800";
      case "Low": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Lesson Processing Complete</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Summary */}
          <div className="flex gap-4 p-4 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <span className="font-semibold">{stats.project_added} Added</span>
            </div>
            {stats.project_deleted > 0 && (
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-orange-600" />
                <span className="font-semibold">{stats.project_deleted} Superseded</span>
              </div>
            )}
          </div>

          {/* New Lessons */}
          {stats.project_new_lessons.length > 0 && (
            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                New Lessons Added
              </h3>
              <div className="space-y-3">
                {stats.project_new_lessons.map((lesson, idx) => (
                  <div key={idx} className="p-4 border rounded-lg bg-green-50">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium">{lesson.title}</h4>
                      <Badge className={getSeverityColor(lesson.severity)}>
                        {lesson.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      <span className="font-medium">Lesson:</span> {lesson.lesson}
                    </p>
                    <p className="text-sm text-muted-foreground mb-2">
                      <span className="font-medium">Impact:</span> {lesson.impact}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      <span className="font-medium">Recommendation:</span> {lesson.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Superseded Lessons */}
          {stats.project_superseded_lessons.length > 0 && (
            <div>
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <XCircle className="h-5 w-5 text-orange-600" />
                Superseded Lessons (Removed)
              </h3>
              <div className="space-y-3">
                {stats.project_superseded_lessons.map((lesson, idx) => (
                  <div key={idx} className="p-4 border rounded-lg bg-orange-50 opacity-75">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium line-through">{lesson.title}</h4>
                      <Badge className={getSeverityColor(lesson.severity)}>
                        {lesson.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      <span className="font-medium">Lesson:</span> {lesson.lesson}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Button onClick={() => onOpenChange(false)}>
              Done
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
