"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { apiRequest } from "@/lib/api";
import { Search, ChevronDown, ChevronUp } from "lucide-react";

interface Source {
  content: string;
  source: string;
  project: string;
  project_type: string;
  category: string;
  relevance_score: number;
}

interface SearchResult {
  answer: string;
  sources: Source[];
}

interface ProjectLessonsSearchProps {
  projectType: string;
}

export default function ProjectLessonsSearch({ projectType }: ProjectLessonsSearchProps) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const [searchType, setSearchType] = useState<"both" | "lessons" | "documents">("both");

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const body: any = {
        query,
        project_type: projectType,
        limit: 10,
      };

      if (searchType === "lessons") {
        body.is_lesson = true;
      } else if (searchType === "documents") {
        body.is_lesson = false;
      }

      const data = await apiRequest("/search-rag", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResult({ answer: data.answer, sources: data.sources || [] });
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (index: number) => {
    const newExpanded = new Set(expandedSources);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSources(newExpanded);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Search Knowledge Base</CardTitle>
        <p className="text-sm text-muted-foreground">
          Search documents and lessons from all {projectType} projects
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search Type Filter */}
        <div className="flex flex-col gap-2">
          <Label>Search Type</Label>
          <div className="flex gap-2">
            <Button
              variant={searchType === "both" ? "default" : "outline"}
              size="sm"
              onClick={() => setSearchType("both")}
            >
              Both
            </Button>
            <Button
              variant={searchType === "lessons" ? "default" : "outline"}
              size="sm"
              onClick={() => setSearchType("lessons")}
            >
              Lessons Only
            </Button>
            <Button
              variant={searchType === "documents" ? "default" : "outline"}
              size="sm"
              onClick={() => setSearchType("documents")}
            >
              Documents Only
            </Button>
          </div>
        </div>

        {/* Search Input */}
        <div className="flex gap-2">
          <Input
            placeholder="Ask a question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <Button onClick={handleSearch} disabled={loading}>
            <Search className="h-4 w-4 mr-2" />
            {loading ? "Searching..." : "Search"}
          </Button>
        </div>

        {result && (
          <div className="space-y-6 mt-6">
            {/* Answer */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Answer</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{result.answer}</p>
              </CardContent>
            </Card>

            {/* Sources */}
            {result.sources.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-semibold text-lg">Lessons from Similar Projects</h3>
                {result.sources.map((source, index) => (
                  <Card key={index} className="border">
                    <CardHeader
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleSource(index)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline">[{index + 1}]</Badge>
                          <div>
                            <p className="font-medium">{source.category || "Lesson"}</p>
                            <p className="text-sm text-muted-foreground">
                              From: {source.project}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">
                            {source.relevance_score}% match
                          </Badge>
                          {expandedSources.has(index) ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    {expandedSources.has(index) && (
                      <CardContent>
                        <p className="text-sm whitespace-pre-wrap bg-muted p-4 rounded">
                          {source.content}
                        </p>
                      </CardContent>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
