"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import ProjectCard from "./ProjectCard";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Upload,
  Search,
  Plus,
  ArrowLeft,
  FileText,
  Users,
  Calendar,
} from "lucide-react";
import UploadDialog from "./UploadDialog";
import CreateProjectDialog from "./CreateProjectDialog";
import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Project {
  name: string;
  status?: string;
  meeting_count?: number;
  action_items?: { open: number; total: number };
  team_size?: number;
  recent_activity?: string[];
  next_tasks?: { task: string; assignee: string }[];
  health?: string;
  description?: string;
  action_items_detail?: any[];
  timeline?: any[];
  meeting_summaries?: any[];
  generated_assets?: any[];
}

export default function Dashboard() {
  const router = useRouter();
  const { apiKey } = useApiKey();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await apiRequest("/projects", {}, apiKey);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error loading projects:", error);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  const showProjectDetail = (projectName: string) => {
    router.push(`/project/${encodeURIComponent(projectName)}`);
  };

  const performGlobalSearch = async () => {
    if (!globalSearch.trim()) return;
    try {
      const response = await apiRequest("/search", {
        method: "POST",
        body: JSON.stringify({ query: globalSearch }),
      }, apiKey);
      if (response.ok) {
        const result = await response.json();
        setSearchResults(result);
      }
    } catch (error) {
      console.error("Error performing search:", error);
    }
  };

  const getStatusVariant = (status?: string) => {
    switch (status) {
      case "completed":
        return "secondary";
      case "on-hold":
        return "outline";
      default:
        return "default";
    }
  };

  const getHealthColor = (project: Project) => {
    if (project.health) return project.health;
    const openActions = project.action_items?.open || 0;
    const totalActions = project.action_items?.total || 0;
    if (totalActions === 0) return "green";
    const ratio = openActions / totalActions;
    if (ratio > 0.7) return "red";
    if (ratio > 0.3) return "yellow";
    return "green";
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card shadow-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center p-6">
          <h1 className="text-3xl font-semibold tracking-tight">
            Meeting Automation Dashboard
          </h1>
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              <Input
                placeholder="Search across all projects..."
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                className="w-80"
              />
              <Button
                variant="secondary"
                onClick={performGlobalSearch}
                className="hover:bg-secondary/80"
              >
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
            </div>
            <Button
              variant="secondary"
              onClick={() => setShowCreateProject(true)}
              className="hover:bg-secondary/80"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
            <Button onClick={() => setShowUpload(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Video
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        {loading ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-12">
            <h2 className="text-2xl font-semibold mb-2">No projects found</h2>
            <p className="text-muted-foreground mb-4">
              Upload a video to create your first project
            </p>
            <Button onClick={() => setShowUpload(true)}>
              <Upload className="h-4 w-4 mr-2" />
              Upload Video
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <ProjectCard
                key={project.name}
                project={project}
                onClick={() => showProjectDetail(project.name)}
                onDelete={() => loadProjects()}
              />
            ))}
          </div>
        )}
      </div>

      <UploadDialog
        open={showUpload}
        onOpenChange={setShowUpload}
        onUploadComplete={loadProjects}
      />

      <CreateProjectDialog
        open={showCreateProject}
        onOpenChange={setShowCreateProject}
        onProjectCreated={loadProjects}
      />
    </div>
  );
}
