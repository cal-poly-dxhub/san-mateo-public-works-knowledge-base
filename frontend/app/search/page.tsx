"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api";
import { Search, ChevronDown, ChevronUp } from "lucide-react";

interface Source {
  content: string;
  source: string;
  project: string;
  relevance_score: number;
  chunk_index: string;
  total_chunks: string;
}

interface SearchResult {
  answer: string;
  sources: Source[];
}

export default function SearchPage() {
  const { apiKey } = useApiKey();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const [searchType, setSearchType] = useState<"both" | "lessons" | "documents">("both");
  const [selectedProject, setSelectedProject] = useState("");
  const [projects, setProjects] = useState<string[]>([]);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (apiKey) {
      loadAvailableModels();
    }
  }, [apiKey]);

  const loadAvailableModels = async () => {
    try {
      const data = await apiRequest("/models");
      const models = Array.isArray(data) ? data : (data.available_search_models || []);
      setAvailableModels(models);
      if (models.length > 0) {
        setSelectedModel(models[0].id);
      }
    } catch (error) {
      console.error("Error loading models:", error);
    }
  };

  const loadProjects = async () => {
    try {
      const data = await apiRequest("/projects");
      setProjects(data.projects?.map((p: any) => p.name) || []);
    } catch (error) {
      console.error("Error loading projects:", error);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const body: any = { query, limit: 10, model_id: selectedModel };
      
      if (selectedProject) {
        body.project_name = selectedProject;
      }
      
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
    <div className="container mx-auto p-6 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Base Search</CardTitle>
          <p className="text-sm text-muted-foreground">
            Search documents and lessons learned across all projects
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

          {/* Project Filter */}
          <div className="flex flex-col gap-2">
            <Label htmlFor="project">Filter by Project (Optional)</Label>
            <select
              id="project"
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">All Projects</option>
              {projects.map((project) => (
                <option key={project} value={project}>
                  {project}
                </option>
              ))}
            </select>
          </div>

          {/* Model Selection */}
          <div className="flex flex-col gap-2">
            <Label htmlFor="model">AI Model</Label>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger id="model">
                <SelectValue placeholder="Select AI Model" />
              </SelectTrigger>
              <SelectContent>
                {availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    {model.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
              {/* Answer with citations */}
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
                  <h3 className="font-semibold text-lg">Sources</h3>
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
                              <p className="font-medium">{source.source}</p>
                              <p className="text-sm text-muted-foreground">
                                Project: {source.project} • Chunk {source.chunk_index}/{source.total_chunks}
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
    </div>
  );
}
