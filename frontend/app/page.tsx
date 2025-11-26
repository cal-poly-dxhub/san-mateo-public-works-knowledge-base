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
import KBSyncButton from "@/components/KBSyncButton";

import { useApi } from "@/lib/api-context";
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
  const { refreshTrigger } = useApi();

  const [hasSearched, setHasSearched] = useState(false);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [searchType, setSearchType] = useState<
    "both" | "lessons" | "documents"
  >("both");
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [searchLimit, setSearchLimit] = useState("5");
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<"alphabetical" | "progress" | "date">(
    "alphabetical",
  );
  const [checklistType, setChecklistType] = useState<"design" | "construction">(
    () => {
      if (typeof window !== "undefined") {
        const stored = sessionStorage.getItem("checklist-type");
        return (stored as "design" | "construction") || "design";
      }
      return "design";
    },
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [projectsPerPage, setProjectsPerPage] = useState(20);
  const [totalProjects, setTotalProjects] = useState(0);

  useEffect(() => {
    const handleChecklistTypeChange = (event: CustomEvent) => {
      setChecklistType(event.detail);
    };

    window.addEventListener(
      "checklistTypeChange",
      handleChecklistTypeChange as EventListener,
    );
    return () =>
      window.removeEventListener(
        "checklistTypeChange",
        handleChecklistTypeChange as EventListener,
      );
  }, []);

  useEffect(() => {
    loadAvailableModels();
  }, []);

  useEffect(() => {
    loadProjects();
  }, [refreshTrigger, checklistType, currentPage, projectsPerPage]);

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
      const offset = (currentPage - 1) * projectsPerPage;
      const data = await apiRequest(
        `/projects?type=${checklistType}&limit=${projectsPerPage}&offset=${offset}`,
      );
      setProjects(
        Array.isArray(data.projects)
          ? data.projects
          : Array.isArray(data)
            ? data
            : [],
      );
      setTotalProjects(data.total || (Array.isArray(data) ? data.length : 0));
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
        setSearchResults([
          {
            answer: data.answer,
            query: searchQuery,
            sources: data.sources || [],
          },
        ]);
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

  const handleProjectCreated = () => {
    loadProjects();
  };

  const getSortedProjects = () => {
    const sorted = [...projects];
    if (sortBy === "alphabetical") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "progress") {
      sorted.sort((a, b) => {
        const progressA = a.task_progress?.total
          ? a.task_progress.completed / a.task_progress.total
          : 0;
        const progressB = b.task_progress?.total
          ? b.task_progress.completed / b.task_progress.total
          : 0;
        return progressB - progressA;
      });
    } else if (sortBy === "date") {
      sorted.sort((a, b) => {
        const dateA = new Date(
          a.next_task?.projected_date || "9999-12-31",
        ).getTime();
        const dateB = new Date(
          b.next_task?.projected_date || "9999-12-31",
        ).getTime();
        return dateA - dateB;
      });
    }

    return sorted;
  };

  const totalPages = Math.ceil(totalProjects / projectsPerPage);

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
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card shadow-sm mb-8">
        <div className="max-w-7xl mx-auto flex justify-between items-center p-4">
          <h1 className="text-2xl font-semibold">Projects</h1>
          <KBSyncButton />
        </div>
      </header>

      <div className="p-4">
        <div className="mb-8">
          <SearchComponent placeholder="Ask the AI Assistant: regulations, templates, timelines..." />
        </div>

        <div className="flex gap-4 mb-8 justify-between items-center">
          <div className="flex gap-4">
            <Button
              variant="secondary"
              onClick={() => setCreateProjectOpen(true)}
            >
              Create Project
            </Button>
          </div>

          <div className="flex gap-2 items-center">
            <Select
              value={projectsPerPage.toString()}
              onValueChange={(value) => {
                setProjectsPerPage(parseInt(value));
                setCurrentPage(1);
              }}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5 per page</SelectItem>
                <SelectItem value="10">10 per page</SelectItem>
                <SelectItem value="20">20 per page</SelectItem>
                <SelectItem value="50">50 per page</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={sortBy}
              onValueChange={(value: any) => setSortBy(value)}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="alphabetical">Alphabetical</SelectItem>
                <SelectItem value="progress">Progress (High to Low)</SelectItem>
                <SelectItem value="date">Earliest Date</SelectItem>
              </SelectContent>
            </Select>
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

        {projects.length === 0 ? (
          <div className="text-center py-16">
            <h2 className="text-2xl font-semibold mb-4">No projects found</h2>
            <p className="text-muted-foreground">
              Upload a video to create your first project
            </p>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {getSortedProjects().map((project) => (
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
            {getSortedProjects().map((project) => {
              const isExpanded = expandedTasks.has(project.name);
              const taskText = project.next_task?.text || "";
              const shouldTruncate = taskText.length > 60;

              return (
                <div
                  key={project.name}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => handleProjectClick(project.name)}
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <h3 className="font-semibold truncate">
                          {project.name}
                        </h3>
                        <span className="text-xs text-muted-foreground whitespace-nowrap">
                          {project.task_progress?.completed || 0}/
                          {project.task_progress?.total || 0}
                        </span>
                      </div>
                      {project.next_task && (
                        <div className="text-xs text-primary">
                          <span className="font-medium">
                            {project.next_task.number}:
                          </span>{" "}
                          {isExpanded || !shouldTruncate
                            ? taskText
                            : `${taskText.substring(0, 60)}...`}
                          {shouldTruncate && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedTasks((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(project.name)) {
                                    next.delete(project.name);
                                  } else {
                                    next.add(project.name);
                                  }
                                  return next;
                                });
                              }}
                              className="ml-1 underline hover:no-underline"
                            >
                              {isExpanded ? "less" : "more"}
                            </button>
                          )}
                          <span className="text-muted-foreground ml-1">
                            • Projected:{" "}
                            {project.next_task.projected_date || "None"}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-lg font-semibold">
                        {project.task_progress?.total
                          ? Math.round(
                              (project.task_progress.completed /
                                project.task_progress.total) *
                                100,
                            )
                          : 0}
                        %
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex justify-center gap-2 mt-8">
            <Button
              variant="outline"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span className="flex items-center px-4">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        )}

        <CreateProjectDialog
          open={createProjectOpen}
          onOpenChange={setCreateProjectOpen}
          onProjectCreated={handleProjectCreated}
        />
      </div>
    </div>
  );
}
