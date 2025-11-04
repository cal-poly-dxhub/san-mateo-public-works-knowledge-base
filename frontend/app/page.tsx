"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, LayoutGrid, List } from "lucide-react";
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
import SearchComponent from "@/components/SearchComponent";

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
  next_task?: {
    number: string;
    text: string;
    projected_date: string;
  };
  health?: string;
}

export default function Home() {
  const router = useRouter();
  const { apiKey, refreshTrigger } = useApiKey();

  const [hasSearched, setHasSearched] = useState(false);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [searchType, setSearchType] = useState<
    "both" | "lessons" | "documents"
  >("both");
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [searchLimit, setSearchLimit] = useState("5");
  const [batchStatusOpen, setBatchStatusOpen] = useState(false);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

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
      const models = Array.isArray(data)
        ? data
        : data.available_search_models || [];
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
      <div className="mb-8">
        <SearchComponent placeholder="Ask the AI Assistant: regulations, templates, timelines..." />
      </div>

      <div className="flex gap-4 mb-8">
      <div className="flex gap-4 mb-8 justify-between items-center">
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
        
        <div className="flex gap-2">
          <Button
            variant={viewMode === "grid" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("grid")}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("list")}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
        </div>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-16">
          <h2 className="text-2xl font-semibold mb-4">No projects found</h2>
          <p className="text-muted-foreground">
            Upload a video to create your first project
          </p>
        </div>
      ) : viewMode === "grid" ? (
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
      ) : (
        <div className="space-y-2">
          {projects.map((project) => {
            const isExpanded = expandedTasks.has(project.name);
            const taskText = project.next_task?.text || "";
            const shouldTruncate = taskText.length > 100;
            
            return (
              <div
                key={project.name}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                onClick={() => handleProjectClick(project.name)}
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className="flex-1">
                    <h3 className="font-semibold">{project.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {project.task_progress?.completed || 0} / {project.task_progress?.total || 0} tasks completed
                    </p>
                    {project.next_task && (
                      <div className="text-sm text-primary mt-1">
                        <span className="font-medium">{project.next_task.number}: </span>
                        {isExpanded || !shouldTruncate
                          ? taskText
                          : `${taskText.substring(0, 100)}...`}
                        {shouldTruncate && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedTasks(prev => {
                                const next = new Set(prev);
                                if (next.has(project.name)) {
                                  next.delete(project.name);
                                } else {
                                  next.add(project.name);
                                }
                                return next;
                              });
                            }}
                            className="ml-2 underline hover:no-underline"
                          >
                            {isExpanded ? "Show less" : "Show more"}
                          </button>
                        )}
                        <span className="text-muted-foreground ml-2">
                          • Projected: {project.next_task.projected_date || "None"}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-semibold">
                      {project.task_progress?.total 
                        ? Math.round((project.task_progress.completed / project.task_progress.total) * 100)
                        : 0}%
                    </div>
                    <div className="text-sm text-muted-foreground">Progress</div>
                  </div>
                </div>
              </div>
            );
          })}
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
