"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api";

interface Task {
  task_id: string;
  phase: string;
  task: string;
  description: string;
  estimatedDays: number;
  dependencies: string[];
  required: boolean;
  completed_date?: string;
  status: string;
}

interface ChecklistProps {
  projectName: string;
}

export default function Checklist({ projectName }: ChecklistProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [progress, setProgress] = useState({ total: 0, completed: 0, percentage: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChecklist();
  }, [projectName]);

  const loadChecklist = async () => {
    try {
      const data = await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist`);
      setTasks(data.tasks || []);
      setProgress(data.progress || { total: 0, completed: 0, percentage: 0 });
    } catch (error) {
      console.error("Error loading checklist:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = async (task: Task) => {
    const newCompletedDate = task.completed_date ? null : new Date().toISOString().split('T')[0];
    
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist`, {
        method: "PUT",
        body: JSON.stringify({
          task_id: task.task_id,
          completed_date: newCompletedDate,
        }),
      });
      
      // Reload checklist to update progress
      loadChecklist();
    } catch (error) {
      console.error("Error updating task:", error);
    }
  };

  // Group tasks by phase
  const tasksByPhase = tasks.reduce((acc, task) => {
    if (!acc[task.phase]) {
      acc[task.phase] = [];
    }
    acc[task.phase].push(task);
    return acc;
  }, {} as Record<string, Task[]>);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">Loading checklist...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <Card>
        <CardHeader>
          <CardTitle>Project Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{progress.completed} of {progress.total} tasks completed</span>
              <span className="font-semibold">{progress.percentage}%</span>
            </div>
            <Progress value={progress.percentage} className="h-3" />
          </div>
        </CardContent>
      </Card>

      {/* Checklist by Phase */}
      <Card>
        <CardHeader>
          <CardTitle>Project Checklist</CardTitle>
          <p className="text-sm text-muted-foreground">
            Track project tasks and milestones
          </p>
        </CardHeader>
        <CardContent>
          {Object.keys(tasksByPhase).length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No tasks found. Tasks will be generated when you create a project.
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(tasksByPhase).map(([phase, phaseTasks]) => (
                <div key={phase}>
                  <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
                    {phase}
                    <Badge variant="secondary">
                      {phaseTasks.filter(t => t.completed_date).length}/{phaseTasks.length}
                    </Badge>
                  </h3>
                  <div className="space-y-2">
                    {phaseTasks.map((task) => (
                      <div
                        key={task.task_id}
                        className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                      >
                        <Checkbox
                          checked={!!task.completed_date}
                          onCheckedChange={() => toggleTask(task)}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className={task.completed_date ? "line-through text-muted-foreground" : ""}>
                              {task.task}
                            </span>
                            {task.required && (
                              <Badge variant="outline" className="text-xs">Required</Badge>
                            )}
                          </div>
                          {task.description && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {task.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span>Est. {task.estimatedDays} days</span>
                            {task.completed_date && (
                              <span className="text-green-600">
                                Completed: {task.completed_date}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
