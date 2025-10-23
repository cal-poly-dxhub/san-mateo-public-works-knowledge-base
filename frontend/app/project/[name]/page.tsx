"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search } from "lucide-react";
import { Switch } from "@/components/ui/switch";
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
import DocumentUploadDialog from "@/components/DocumentUploadDialog";
import LessonsLearned from "@/components/LessonsLearned";
import Checklist from "@/components/Checklist";

interface Project {
  name: string;
  projectType?: string;
  status?: string;
  description?: string;
  project_overview?: any;
  action_items_detail?: Array<{
    title?: string;
    description?: string;
    assignee?: string;
    due_date?: string;
    status?: string;
    meeting_date?: string;
  }>;
  timeline?: any[];
  meeting_summaries?: any[];
  generated_assets?: any[];
}

export default function ProjectPage() {
  const params = useParams();
  const router = useRouter();
  const { apiKey } = useApiKey();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [projectSearch, setProjectSearch] = useState("");
  const [ragEnabled, setRagEnabled] = useState(true);
  const [searchLimit, setSearchLimit] = useState("5");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [searchType, setSearchType] = useState<"both" | "lessons" | "documents">("both");

  useEffect(() => {
    if (params.name) {
      loadProject(decodeURIComponent(params.name as string));
    }
  }, [params.name]);

  useEffect(() => {
    if (apiKey) {
      loadAvailableModels();
    }
  }, [apiKey]);

  const loadAvailableModels = async () => {
    try {
      const data = await apiRequest("/models");
      console.log("Models API response:", data);
      const models = Array.isArray(data) ? data : (data.available_search_models || []);
      console.log("Parsed models:", models);
      setAvailableModels(models);
      if (models.length > 0) {
        setSelectedModel(models[0].id);
      }
    } catch (error) {
      console.error("Error loading models:", error);
    }
  };

  const loadProject = async (projectName: string) => {
    try {
      const data = await apiRequest(
        `/projects/${encodeURIComponent(projectName)}`,
      );
      setProject(data);
    } catch (error) {
      console.error("Error loading project:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSearch = async () => {
    if (!projectSearch.trim() || !project) return;

    setIsSearching(true);
    setSearchResults([]);
    try {
      const endpoint = ragEnabled ? "/search-rag" : "/project-search";
      const body: any = {
        query: projectSearch,
        project_name: project?.name,
        limit: parseInt(searchLimit),
        model_id: selectedModel,
      };

      if (ragEnabled && searchType === "lessons") {
        body.is_lesson = true;
      } else if (ragEnabled && searchType === "documents") {
        body.is_lesson = false;
      }

      const data = await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });

      if (ragEnabled) {
        setSearchResults([{ answer: data.answer, query: projectSearch }]);
      } else {
        setSearchResults(data.results || []);
      }
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
      setHasSearched(true);
    }
  };

  const generateExecutiveReview = async () => {
    if (!project) return;

    setIsGeneratingReview(true);
    try {
      // Start the generation
      const data = await apiRequest(
        `/projects/${encodeURIComponent(project.name)}/executive-summary`,
        { method: "POST" },
      );

      if (data.status === "processing") {
        // Poll for the file to be ready
        const maxAttempts = 30; // 5 minutes max
        let attempts = 0;

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 10000)); // Wait 10 seconds
          attempts++;

          try {
            const response = await fetch(
              `${process.env.NEXT_PUBLIC_API_URL || "https://42redkfdhl.execute-api.us-west-2.amazonaws.com/prod"}/projects/${encodeURIComponent(project.name)}/assets/executive_summary.md`,
              {
                headers: {
                  "x-api-key":
                    process.env.NEXT_PUBLIC_API_KEY ||
                    localStorage?.getItem("apiKey") ||
                    "",
                },
              },
            );

            if (response.ok) {
              const contentResponse = await response.text();

              // Create and download the file
              const blob = new Blob([contentResponse], {
                type: "text/markdown",
              });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `${project.name}_executive_summary.md`;
              link.click();
              URL.revokeObjectURL(url);

              // Refresh asset availability
              checkAssetAvailability(project);
              return;
            }
          } catch (pollError) {
            // Continue polling
          }
        }

        throw new Error("Generation timed out. Please try again.");
      }
    } catch (error) {
      console.error("Error generating executive review:", error);
      alert("Error generating executive review");
    } finally {
      setIsGeneratingReview(false);
    }
  };

  const generateWebStory = async () => {
    if (!project) return;

    setIsGeneratingStory(true);
    try {
      // Start the generation
      const data = await apiRequest(
        `/projects/${encodeURIComponent(project.name)}/webstory`,
        { method: "POST" },
      );

      if (data.status === "processing") {
        // Poll for the file to be ready
        const maxAttempts = 30; // 5 minutes max
        let attempts = 0;

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 10000)); // Wait 10 seconds
          attempts++;

          try {
            const response = await fetch(
              `${process.env.NEXT_PUBLIC_API_URL || "https://42redkfdhl.execute-api.us-west-2.amazonaws.com/prod"}/projects/${encodeURIComponent(project.name)}/assets/webstory.md`,
              {
                headers: {
                  "x-api-key":
                    process.env.NEXT_PUBLIC_API_KEY ||
                    localStorage?.getItem("apiKey") ||
                    "",
                },
              },
            );

            if (response.ok) {
              const contentResponse = await response.text();

              // Create and download the file
              const blob = new Blob([contentResponse], {
                type: "text/markdown",
              });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `${project.name}_webstory.md`;
              link.click();
              URL.revokeObjectURL(url);

              // Refresh asset availability
              checkAssetAvailability(project);
              return;
            }
          } catch (pollError) {
            // Continue polling
          }
        }

        throw new Error("Generation timed out. Please try again.");
      }
    } catch (error) {
      console.error("Error generating web story:", error);
      alert("Error generating web story");
    } finally {
      setIsGeneratingStory(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">Project not found</h2>
          <Button onClick={() => router.push("/")}>Back to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card shadow-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center p-6">
          <h1 className="text-3xl font-semibold tracking-tight">
            {project?.name || "Loading..."}
          </h1>
          <Button
            onClick={() => setUploadDialogOpen(true)}
            variant="outline"
            size="sm"
          >
            Upload Document
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        <div className="space-y-4 mb-6">
          {/* Suggested Questions */}
          <div className="flex gap-2 items-center">
            <span className="text-sm text-muted-foreground">Suggested:</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setProjectSearch("Im starting a new project, anything I should be aware of?")}
            >
              Im starting a new project, anything I should be aware of?
            </Button>
          </div>

          {/* Search Type Filter */}
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

          {/* Search Bar */}
          <div className="flex gap-4">
            <Input
              placeholder="Search within this project..."
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleProjectSearch()}
              className="flex-1"
            />
            {ragEnabled && (
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="w-48">
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
            )}
            <div className="flex items-center space-x-2">
              <Switch
                id="rag-toggle"
                checked={ragEnabled}
                onCheckedChange={setRagEnabled}
              />
              <Label htmlFor="rag-toggle" className="text-sm whitespace-nowrap">
                RAG
              </Label>
            </div>
            <Select value={searchLimit} onValueChange={setSearchLimit}>
              <SelectTrigger className="w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3</SelectItem>
                <SelectItem value="5">5</SelectItem>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleProjectSearch}
              disabled={isSearching}
              className="hover:bg-primary/90"
            >
              <Search className="h-4 w-4 mr-2" />
              {isSearching ? "Searching..." : "Search"}
            </Button>
          </div>
        </div>

        {hasSearched && (
          <div className="mb-6">
            <Card>
              <CardHeader>
                <CardTitle>Search Results</CardTitle>
              </CardHeader>
              <CardContent>
                {searchResults.length > 0 ? (
                  ragEnabled ? (
                    <div className="space-y-4">
                      <h4 className="font-medium">AI Answer:</h4>
                      <p className="text-sm leading-relaxed">
                        {searchResults[0]?.answer}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {searchResults.map((result, index) => (
                        <div key={index} className="p-4 border rounded-lg">
                          <h4 className="font-medium">
                            {result.title || result.source}
                          </h4>
                          <p className="text-sm text-gray-600 mt-2">
                            {result.content || result.text}
                          </p>
                          {result.score && (
                            <span className="text-xs text-gray-400">
                              Score: {result.score.toFixed(3)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                ) : (
                  <div className="text-center text-muted-foreground py-4">
                    No results found for "{projectSearch}"
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Removed project overview and status cards - now handled in tabs */}

        <Tabs defaultValue="checklist" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="checklist">Checklist</TabsTrigger>
            <TabsTrigger value="lessons">Lessons Learned</TabsTrigger>
          </TabsList>

          <TabsContent value="checklist" className="space-y-6">
            <Checklist projectName={project.name} />
          </TabsContent>

          <TabsContent value="lessons" className="space-y-6">
            <LessonsLearned projectName={project.name} />
          </TabsContent>
        </Tabs>
      </div>

      <DocumentUploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        projectName={project?.name || ""}
        projectType={project?.projectType || "other"}
        onUploadComplete={() => {
          // Refresh lessons learned
          setUploadDialogOpen(false);
        }}
      />
    </div>
  );
}
