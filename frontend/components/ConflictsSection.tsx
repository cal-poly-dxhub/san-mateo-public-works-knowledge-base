"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface Conflict {
  id: string;
  new_lesson: any;
  existing_lesson: any;
  reason: string;
  status: string;
}

interface ConflictsSectionProps {
  projectName: string;
  onResolved: () => void;
}

export default function ConflictsSection({ projectName, onResolved }: ConflictsSectionProps) {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConflicts();
  }, [projectName]);

  const loadConflicts = async () => {
    try {
      const data = await apiRequest(`/projects/${encodeURIComponent(projectName)}/conflicts`);
      setConflicts(data.conflicts || []);
    } catch (error) {
      console.error("Error loading conflicts:", error);
    } finally {
      setLoading(false);
    }
  };

  const resolveConflict = async (conflictId: string, decision: string) => {
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/conflicts/resolve`, {
        method: "POST",
        body: JSON.stringify({ conflict_id: conflictId, decision }),
      });
      
      setConflicts(conflicts.filter(c => c.id !== conflictId));
      onResolved();
    } catch (error) {
      console.error("Error resolving conflict:", error);
      alert("Error resolving conflict");
    }
  };

  if (loading) return null;
  if (conflicts.length === 0) return null;

  return (
    <Card className="border-orange-200 bg-orange-50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-orange-800">
          <AlertTriangle className="h-5 w-5" />
          {conflicts.length} Lesson Conflict{conflicts.length > 1 ? "s" : ""} Need Review
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {conflicts.map((conflict) => (
          <div key={conflict.id} className="bg-white p-4 rounded-lg border space-y-4">
            <div className="text-sm text-muted-foreground mb-3">
              <strong>Reason:</strong> {conflict.reason}
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* New Lesson */}
              <div className="border-l-4 border-l-green-500 pl-3">
                <Badge className="mb-2 bg-green-100 text-green-800">New Lesson</Badge>
                <h4 className="font-semibold mb-2">{conflict.new_lesson.title}</h4>
                <p className="text-sm text-muted-foreground mb-1">
                  <strong>Lesson:</strong> {conflict.new_lesson.lesson}
                </p>
                <p className="text-sm text-muted-foreground">
                  <strong>Impact:</strong> {conflict.new_lesson.impact}
                </p>
              </div>

              {/* Existing Lesson */}
              <div className="border-l-4 border-l-blue-500 pl-3">
                <Badge className="mb-2 bg-blue-100 text-blue-800">Existing Lesson</Badge>
                <h4 className="font-semibold mb-2">{conflict.existing_lesson.title}</h4>
                <p className="text-sm text-muted-foreground mb-1">
                  <strong>Lesson:</strong> {conflict.existing_lesson.lesson}
                </p>
                <p className="text-sm text-muted-foreground">
                  <strong>Impact:</strong> {conflict.existing_lesson.impact}
                </p>
              </div>
            </div>

            <div className="flex gap-2 justify-end pt-2 border-t">
              <Button
                size="sm"
                variant="outline"
                onClick={() => resolveConflict(conflict.id, "keep_new")}
              >
                Keep New
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => resolveConflict(conflict.id, "keep_existing")}
              >
                Keep Existing
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={() => resolveConflict(conflict.id, "keep_both")}
              >
                Keep Both
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => resolveConflict(conflict.id, "delete_both")}
              >
                Delete Both
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
