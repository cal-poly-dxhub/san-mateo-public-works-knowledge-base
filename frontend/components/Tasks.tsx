"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { apiRequest } from "@/lib/api";

interface Task {
  taskId: string;
  phase: string;
  taskName: string;
  description?: string;
  status: "not_started" | "in_progress" | "completed";
  estimatedDays?: number;
  assignedTo?: string;
  plannedCompletionDate?: string;
  actualCompletionDate?: string;
}

interface TasksProps {
  projectName: string;
}

export default function Tasks({ projectName }: TasksProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    loadTasks();
  }, [projectName]);

  const loadTasks = async () => {
    try {
      const data = await apiRequest(`/projects/${encodeURIComponent(projectName)}/tasks`);
      setTasks(data.tasks || []);
      setProgress(data.progress || 0);
    } catch (error) {
      console.error("Error loading tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (taskId: string, newStatus: string) => {
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/tasks/${taskId}`, {
        method: "PUT",
        body: JSON.stringify({ status: newStatus }),
      });
      loadTasks();
    } catch (error) {
      console.error("Error updating task:", error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "bg-green-500";
      case "in_progress": return "bg-yellow-500";
      default: return "bg-gray-300";
    }
  };

  const groupedTasks = tasks.reduce((acc, task) => {
    if (!acc[task.phase]) acc[task.phase] = [];
    acc[task.phase].push(task);
    return acc;
  }, {} as Record<string, Task[]>);

  if (loading) return <div>Loading tasks...</div>;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex justify-between items-center">
            <span>Project Progress</span>
            <span className="text-2xl">{progress}%</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div className="bg-blue-600 h-4 rounded-full" style={{ width: `${progress}%` }} />
          </div>
        </CardContent>
      </Card>

      {Object.entries(groupedTasks).map(([phase, phaseTasks]) => (
        <Card key={phase}>
          <CardHeader>
            <CardTitle>{phase}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {phaseTasks.map((task) => (
                <div key={task.taskId} className="flex items-start gap-3 p-3 border rounded-lg">
                  <Checkbox
                    checked={task.status === "completed"}
                    onCheckedChange={(checked) => 
                      updateTaskStatus(task.taskId, checked ? "completed" : "not_started")
                    }
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{task.taskName}</h4>
                      <Badge className={getStatusColor(task.status)}>
                        {task.status.replace("_", " ")}
                      </Badge>
                    </div>
                    {task.description && (
                      <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
                    )}
                    <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                      {task.assignedTo && <span>Assigned: {task.assignedTo}</span>}
                      {task.estimatedDays && <span>Est: {task.estimatedDays} days</span>}
                      {task.plannedCompletionDate && <span>Due: {task.plannedCompletionDate}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
