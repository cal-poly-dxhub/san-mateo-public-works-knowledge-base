"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { useState } from "react";
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

interface ProjectCardProps {
  project: Project;
  onClick: () => void;
  onDelete?: () => void;
}

export default function ProjectCard({ project, onClick, onDelete }: ProjectCardProps) {
  const { apiKey } = useApiKey();
  const [deleting, setDeleting] = useState(false);

  const deleteProject = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to delete project "${project.name}"? This action cannot be undone.`)) {
      return;
    }
    
    setDeleting(true);
    try {
      await apiRequest(`/projects/${encodeURIComponent(project.name)}`, {
        method: "DELETE"
      });
      
      alert(`Project "${project.name}" deleted successfully`);
      onDelete?.();
    } catch (error) {
      console.error("Error deleting project:", error);
      alert("Error deleting project");
    } finally {
      setDeleting(false);
    }
  };

  const getStatusVariant = (status?: string) => {
    switch (status) {
      case "active":
        return "default";
      case "completed":
        return "secondary";
      case "on-hold":
        return "destructive";
      default:
        return "default";
    }
  };

  const getHealthColor = (health?: string) => {
    switch (health) {
      case "green":
        return "bg-green-500";
      case "yellow":
        return "bg-yellow-500";
      case "red":
        return "bg-red-500";
      default:
        return "bg-green-500";
    }
  };

  const getProjectHealth = (project: Project) => {
    if (project.health) return project.health;
    const completed = project.task_progress?.completed || 0;
    const total = project.task_progress?.total || 0;
    if (total === 0) return "green";
    const ratio = completed / total;
    if (ratio < 0.3) return "red";
    if (ratio < 0.7) return "yellow";
    return "green";
  };

  const health = getProjectHealth(project);

  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-all duration-300"
      onClick={onClick}
    >
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <h3 className="text-lg font-semibold">{project.name}</h3>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusVariant(project.status)}>
            {project.status
              ? project.status.charAt(0).toUpperCase() + project.status.slice(1)
              : "Active"}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={deleteProject}
            disabled={deleting}
            className="text-red-500 hover:text-red-700 hover:bg-red-50"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-semibold">
              {project.task_count || 0}
            </div>
            <div className="text-sm text-muted-foreground">Total Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-semibold">
              {project.task_progress?.completed || 0}/
              {project.task_progress?.total || 0}
            </div>
            <div className="text-sm text-muted-foreground">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-semibold">
              {project.task_progress?.total 
                ? Math.round((project.task_progress.completed / project.task_progress.total) * 100)
                : 0}%
            </div>
            <div className="text-sm text-muted-foreground">Progress</div>
          </div>
        </div>

        <div className="border-t pt-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <div
              className={`w-3 h-3 rounded-full ${getHealthColor(health)}`}
            ></div>
            <span className="font-medium">Project Health</span>
          </div>
          {project.recent_activity?.slice(0, 2).map((activity, index) => (
            <div key={index} className="text-sm text-muted-foreground mb-1">
              {activity}
            </div>
          )) || (
            <div className="text-sm text-muted-foreground">
              No recent activity
            </div>
          )}
        </div>

        <div className="border-t pt-4">
          <div className="font-medium mb-2">Next Tasks</div>
          {project.next_tasks?.slice(0, 3).map((task, index) => (
            <div key={index} className="text-sm mb-1">
              • {task.task} -{" "}
              <span className="font-medium text-primary">{task.assignee}</span>
            </div>
          )) || (
            <div className="text-sm text-muted-foreground">
              No tasks assigned
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
