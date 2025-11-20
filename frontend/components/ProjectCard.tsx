"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { useApi } from "@/lib/api-context";
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
  next_task?: {
    number: string;
    text: string;
    projected_date: string;
  };
  health?: string;
}

interface ProjectCardProps {
  project: Project;
  onClick: () => void;
  onDelete?: () => void;
}

export default function ProjectCard({ project, onClick, onDelete }: ProjectCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [expanded, setExpanded] = useState(false);

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

        <div className="border-t pt-4">
          <div className="font-medium mb-2">Next Task</div>
          {project.next_task ? (
            <div className="text-sm">
              <div className="font-medium text-primary mb-1">
                {project.next_task.number}
              </div>
              <div className="mb-1">
                {expanded || project.next_task.text.length <= 100
                  ? project.next_task.text
                  : `${project.next_task.text.substring(0, 100)}...`}
                {project.next_task.text.length > 100 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpanded(!expanded);
                    }}
                    className="ml-2 text-primary hover:underline"
                  >
                    {expanded ? "Show less" : "Show more"}
                  </button>
                )}
              </div>
              {project.next_task.projected_date && (
                <div className="text-muted-foreground">
                  Projected: {project.next_task.projected_date}
                </div>
              )}
              {!project.next_task.projected_date && (
                <div className="text-muted-foreground">
                  Projected: None
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No tasks assigned
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
