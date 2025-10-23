"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import ProjectCard from "@/components/ProjectCard";
import CreateProjectDialog from "@/components/CreateProjectDialog";
import BatchStatusDialog from "@/components/BatchStatusDialog";

import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api";

interface Project {
  name: string;
  status?: string;
  task_count?: number;
  task_progress?: {
    completed: number;
    total: number;
  };
  team_size?: number;
  recent_activity?: string[];
  next_tasks?: Array<{
    task: string;
    assignee: string;
  }>;
  health?: string;
}

export default function Home() {
  const router = useRouter();
  const { apiKey, refreshTrigger } = useApiKey();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [searchType, setSearchType] = useState<"both" | "lessons" | "documents">("both");
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [searchLimit, setSearchLimit] = useState("5");
  const [batchStatusOpen, setBatchStatusOpen] = useState(false);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);


  useEffect(() => {
    loadProjects();
  }, [refreshTrigger]);

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
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error loading projects:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectClick = (projectName: string) => {
    router.push(`/project/${encodeURIComponent(projectName)}`);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchResults([]);
    try {
      const endpoint = ragEnabled ? "/search-rag" : "/search";
      const body: any = {
        query: searchQuery,
        model_id: selectedModel,
        limit: parseInt(searchLimit),
      };
      
      if (searchType === "lessons") {
        body.is_lesson = true;
      } else if (searchType === "documents") {
        body.is_lesson = false;
      }
      
      const data = await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });

      if (ragEnabled) {
        setSearchResults([{ answer: data.answer, query: searchQuery }]);
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

  const handleProjectCreated = (batchId?: string) => {
    loadProjects();
    if (batchId) {
      setCurrentBatchId(batchId);
      setBatchStatusOpen(true);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-lg">Loading projects...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="flex justify-between mb-8 gap-4 flex-col">
        <div className="flex gap-4">
          <Input
            type="text"
            placeholder="Ask the AI Assistant: regulations, templates, timelines..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          {ragEnabled && (
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select AI Model" />
              </SelectTrigger>
              <SelectContent>
                {availableModels.length > 0 ? (
                  availableModels.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      {model.name}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="loading" disabled>
                    Loading models... ({availableModels.length})
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          )}
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
          <div className="flex gap-1">
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
              Lessons
            </Button>
            <Button
              variant={searchType === "documents" ? "default" : "outline"}
              size="sm"
              onClick={() => setSearchType("documents")}
            >
              Docs
            </Button>
          </div>
          <Button
            onClick={handleSearch}
            variant="secondary"
            disabled={isSearching}
          >
            {isSearching ? "Searching..." : "Search"}
          </Button>
        </div>
        <div className="flex gap-4">
          <Button
            variant="secondary"
            onClick={() => setCreateProjectOpen(true)}
          >
            Create Project
          </Button>

          {currentBatchId && (
            <Button variant="outline" onClick={() => setBatchStatusOpen(true)}>
              View Batch Status
            </Button>
          )}
        </div>
      </div>

      {hasSearched && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Search Results</h2>
          {searchResults.length > 0 ? (
            <div className="space-y-4">
              {ragEnabled ? (
                <div className="p-4 border rounded-lg">
                  <h3 className="font-medium">AI Answer:</h3>
                  <p className="text-sm leading-relaxed mt-2">
                    {searchResults[0]?.answer}
                  </p>
                </div>
              ) : (
                searchResults.map((result, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <h3 className="font-medium">
                      {result.title || result.source}
                    </h3>
                    <p className="text-sm text-gray-600 mt-2">
                      {result.content || result.text}
                    </p>
                    {result.score && (
                      <span className="text-xs text-gray-400">
                        Score: {result.score.toFixed(3)}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="p-4 border rounded-lg text-center text-muted-foreground">
              No results found for "{searchQuery}"
            </div>
          )}
        </div>
      )}

      {projects.length === 0 ? (
        <div className="text-center py-16">
          <h2 className="text-2xl font-semibold mb-4">No projects found</h2>
          <p className="text-muted-foreground">
            Upload a video to create your first project
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <ProjectCard
              key={project.name}
              project={project}
              onClick={() => handleProjectClick(project.name)}
              onDelete={loadProjects}
            />
          ))}
        </div>
      )}

      <CreateProjectDialog
        open={createProjectOpen}
        onOpenChange={setCreateProjectOpen}
        onProjectCreated={handleProjectCreated}
      />

      <BatchStatusDialog
        open={batchStatusOpen}
        onOpenChange={setBatchStatusOpen}
        batchId={currentBatchId}
      />


    </div>
  );
}
