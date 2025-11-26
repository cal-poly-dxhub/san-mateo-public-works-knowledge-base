"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";
import { useApi } from "@/lib/api-context";
import ConflictsSection from "./ConflictsSection";

interface Lesson {
  title: string;
  id: string;
  lesson: string;
  impact: string;
  recommendation: string;
  severity: "Low" | "Medium" | "High";
  source_document?: string;
  source_content?: string;
  created_at?: string;
}

interface LessonsData {
  projectName: string;
  lastUpdated: string;
  lessons: Lesson[];
}

interface LessonsLearnedProps {
  projectName: string;
}

export default function LessonsLearned({ projectName }: LessonsLearnedProps) {
  const [lessonsData, setLessonsData] = useState<LessonsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLessons();
  }, [projectName]);

  const loadLessons = async () => {
    try {
      const data = await apiRequest(`/projects/${encodeURIComponent(projectName)}/lessons-learned`);
      setLessonsData(data);
    } catch (error) {
      console.error("Error loading lessons:", error);
    } finally {
      setLoading(false);
    }
  };

  const openSourceFile = async (filename: string) => {
    try {
      const response = await apiRequest(`/file/${encodeURIComponent(filename)}`);
      window.open(response.url, '_blank');
    } catch (error) {
      console.error('Error opening file:', error);
      alert('Failed to open file');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "High": return "bg-red-100 text-red-800 border-red-200";
      case "Medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "Low": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const sortedLessons = lessonsData?.lessons.sort((a, b) => {
    const severityOrder = { "High": 3, "Medium": 2, "Low": 1 };
    return severityOrder[b.severity] - severityOrder[a.severity];
  }) || [];

  if (loading) return <div>Loading lessons learned...</div>;

  return (
    <div className="space-y-4">
      <ConflictsSection projectName={projectName} onResolved={loadLessons} />

      {sortedLessons.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No lessons learned yet for this project.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Lessons Learned ({sortedLessons.length})</h3>
          </div>
          
          {sortedLessons.map((lesson, index) => (
            <Card key={lesson.id} className="border-l-4 border-l-current">
              <CardHeader className="pb-0">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-base">{lesson.title}</CardTitle>
                    {lesson.created_at && (
                      <span className="text-xs text-muted-foreground">
                        {new Date(lesson.created_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <Badge className={getSeverityColor(lesson.severity)}>
                    {lesson.severity}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 pt-0">
                <div>
                  <span className="font-medium text-sm">Lesson:</span>
                  <span className="text-sm ml-2">{lesson.lesson}</span>
                </div>
                <div>
                  <span className="font-medium text-sm">Impact:</span>
                  <span className="text-sm ml-2 text-muted-foreground">{lesson.impact}</span>
                </div>
                <div>
                  <span className="font-medium text-sm">Recommendation:</span>
                  <span className="text-sm ml-2 text-muted-foreground">{lesson.recommendation}</span>
                </div>
                {lesson.source_document && (
                  <div>
                    <span className="font-medium text-sm">Source:</span>
                    <button
                      onClick={() => openSourceFile(lesson.source_document!)}
                      className="text-sm ml-2 text-primary hover:underline"
                    >
                      {lesson.source_document}
                    </button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}
