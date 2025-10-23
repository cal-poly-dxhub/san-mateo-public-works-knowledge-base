"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface LessonsLearnedProps {
  projectName: string;
}

export default function LessonsLearned({ projectName }: LessonsLearnedProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLessons();
  }, [projectName]);

  const loadLessons = async () => {
    try {
      const data = await apiRequest(
        `/projects/${encodeURIComponent(projectName)}/lessons-learned`
      );
      setContent(data.content || "No lessons learned yet.");
    } catch (error) {
      console.error("Error loading lessons:", error);
      setContent("Error loading lessons learned.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            Loading lessons learned...
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lessons Learned</CardTitle>
        <p className="text-sm text-muted-foreground">
          Key insights and learnings from this project
        </p>
      </CardHeader>
      <CardContent>
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
}
