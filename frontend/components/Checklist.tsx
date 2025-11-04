"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Pencil, Trash2, Plus, Save, X } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface Task {
  task_id: string;
  checklist_task_id: string;
  description: string;
  projected_date: string;
  actual_date: string;
  required: boolean;
  notes: string;
  status: string;
}

interface Metadata {
  date: string;
  project: string;
  work_authorization: string;
  office_plans_file_no: string;
  design_engineer: string;
  survey_books: string;
  project_manager: string;
  project_type?: string;
  location?: string;
  area_size?: string;
  special_conditions?: string[];
}

interface ChecklistProps {
  projectName: string;
}

export default function Checklist({ projectName }: ChecklistProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [editingMetadata, setEditingMetadata] = useState(false);
  const [editedMetadata, setEditedMetadata] = useState<Metadata | null>(null);
  const [progress, setProgress] = useState({ total: 0, completed: 0, percentage: 0 });
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [editedTask, setEditedTask] = useState<Task | null>(null);
  const [addingTask, setAddingTask] = useState(false);
  const [newTask, setNewTask] = useState<Partial<Task>>({
    checklist_task_id: "",
    description: "",
    projected_date: "",
    required: true,
    notes: ""
  });

  useEffect(() => {
    loadChecklist();
  }, [projectName]);

  const loadChecklist = async () => {
    try {
      const data = await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist`);
      
      const sortedTasks = (data.tasks || []).sort((a, b) => {
        const parseTaskId = (id: string) => id.split('.').map(Number);
        const aParts = parseTaskId(a.checklist_task_id);
        const bParts = parseTaskId(b.checklist_task_id);
        
        for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
          const aVal = aParts[i] || 0;
          const bVal = bParts[i] || 0;
          if (aVal !== bVal) return aVal - bVal;
        }
        return 0;
      });
      
      setTasks(sortedTasks);
      setMetadata(data.metadata || null);
      setEditedMetadata(data.metadata || null);
      setProgress(data.progress || { total: 0, completed: 0, percentage: 0 });
    } catch (error) {
      console.error("Error loading checklist:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = async (task: Task) => {
    const newCompletedDate = task.actual_date ? '' : new Date().toISOString().split('T')[0];
    
    // Update UI immediately
    setTasks(tasks.map(t => 
      t.task_id === task.task_id 
        ? { ...t, actual_date: newCompletedDate, status: newCompletedDate ? 'completed' : 'not_started' }
        : t
    ));
    
    const newCompleted = progress.completed + (newCompletedDate ? 1 : -1);
    setProgress({
      ...progress,
      completed: newCompleted,
      percentage: Math.round((newCompleted / progress.total) * 100)
    });
    
    // Update backend
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist`, {
        method: "PUT",
        body: JSON.stringify({
          task_id: task.task_id,
          completed_date: newCompletedDate || null,
          actual_date: newCompletedDate,
        }),
      });
    } catch (error) {
      console.error("Error updating task:", error);
      loadChecklist();
    }
  };

  const updateTaskDate = async (task: Task, field: 'projected_date' | 'actual_date', value: string) => {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
    
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist`, {
        method: "PUT",
        body: JSON.stringify({
          task_id: task.task_id,
          [field]: value,
          completed_date: field === 'actual_date' && value ? value : (task.actual_date || null),
        }),
      });
      
      loadChecklist();
    } catch (error) {
      console.error("Error updating task date:", error);
    }
  };

  const saveMetadata = async () => {
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/metadata`, {
        method: "PUT",
        body: JSON.stringify(editedMetadata),
      });
      setMetadata(editedMetadata);
      setEditingMetadata(false);
    } catch (error) {
      console.error("Error updating metadata:", error);
    }
  };

  const handleAddTask = async () => {
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist/task`, {
        method: "POST",
        body: JSON.stringify(newTask),
      });
      setAddingTask(false);
      setNewTask({ checklist_task_id: "", description: "", projected_date: "", required: true, notes: "" });
      loadChecklist();
    } catch (error: any) {
      alert(error?.message || "Failed to add task");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist/task`, {
        method: "DELETE",
        body: JSON.stringify({ task_id: taskId }),
      });
      loadChecklist();
    } catch (error) {
      console.error("Error deleting task:", error);
    }
  };

  const handleEditTask = async () => {
    if (!editedTask) return;
    try {
      await apiRequest(`/projects/${encodeURIComponent(projectName)}/checklist/task`, {
        method: "PUT",
        body: JSON.stringify(editedTask),
      });
      setEditingTask(null);
      setEditedTask(null);
      loadChecklist();
    } catch (error: any) {
      alert(error?.message || "Failed to update task");
    }
  };

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
      {/* Project Metadata */}
      {metadata && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Project Information</CardTitle>
              {!editingMetadata ? (
                <Button variant="outline" size="sm" onClick={() => setEditingMetadata(true)}>
                  Edit
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => {
                    setEditedMetadata(metadata);
                    setEditingMetadata(false);
                  }}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={saveMetadata}>
                    Save
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {/* Project Overview Section */}
              <div className="col-span-2">
                <h4 className="font-semibold text-base mb-3 text-primary">Project Overview</h4>
              </div>
              
              <div>
                <span className="font-medium">Project Type:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.project_type || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, project_type: e.target.value })}
                    className="h-8 mt-1"
                    placeholder="e.g., Road Reconstruction"
                  />
                ) : (
                  metadata.project_type || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              
              <div>
                <span className="font-medium">Location:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.location || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, location: e.target.value })}
                    className="h-8 mt-1"
                    placeholder="e.g., Main St between 1st and 5th Ave"
                  />
                ) : (
                  metadata.location || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              
              <div>
                <span className="font-medium">Work Area Size:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.area_size || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, area_size: e.target.value })}
                    className="h-8 mt-1"
                    placeholder="acres"
                  />
                ) : (
                  metadata.area_size ? `${metadata.area_size} acres` : <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              
              <div>
                <span className="font-medium">Special Conditions:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.special_conditions?.join(', ') || ''}
                    onChange={(e) => setEditedMetadata({ 
                      ...editedMetadata!, 
                      special_conditions: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                    })}
                    className="h-8 mt-1"
                    placeholder="e.g., School zone, High traffic"
                  />
                ) : (
                  metadata.special_conditions?.length ? metadata.special_conditions.join(', ') : <span className="text-muted-foreground">None</span>
                )}
              </div>

              {/* Administrative Details Section */}
              <div className="col-span-2 mt-4">
                <h4 className="font-semibold text-base mb-3 text-primary">Administrative Details</h4>
              </div>
              
              <div>
                <span className="font-medium">Date:</span>{" "}
                {editingMetadata ? (
                  <Input
                    type="date"
                    value={editedMetadata?.date || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, date: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.date || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Project:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.project || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, project: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.project || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Work Authorization:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.work_authorization || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, work_authorization: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.work_authorization || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Office Plans File No:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.office_plans_file_no || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, office_plans_file_no: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.office_plans_file_no || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Design Engineer:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.design_engineer || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, design_engineer: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.design_engineer || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Survey Books:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.survey_books || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, survey_books: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.survey_books || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
              <div>
                <span className="font-medium">Project Manager:</span>{" "}
                {editingMetadata ? (
                  <Input
                    value={editedMetadata?.project_manager || ''}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata!, project_manager: e.target.value })}
                    className="h-8 mt-1"
                  />
                ) : (
                  metadata.project_manager || <span className="text-muted-foreground">Not set</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

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

      {/* Checklist */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Project Checklist</CardTitle>
              <p className="text-sm text-muted-foreground">
                Track project tasks and milestones
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="edit-mode">Edit Mode</Label>
              <Switch id="edit-mode" checked={editMode} onCheckedChange={setEditMode} />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {editMode && (
            <Button onClick={() => setAddingTask(true)} className="mb-4" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Task
            </Button>
          )}
          
          {addingTask && (
            <div className="mb-4 p-4 border rounded-lg space-y-2">
              <Input
                placeholder="Task Number (e.g., 3.2)"
                value={newTask.checklist_task_id}
                onChange={(e) => setNewTask({ ...newTask, checklist_task_id: e.target.value })}
              />
              <Input
                placeholder="Description"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
              />
              <Input
                type="date"
                placeholder="Projected Date"
                value={newTask.projected_date}
                onChange={(e) => setNewTask({ ...newTask, projected_date: e.target.value })}
              />
              <div className="flex gap-2">
                <Button onClick={handleAddTask} size="sm">
                  <Save className="h-4 w-4 mr-2" />
                  Save
                </Button>
                <Button onClick={() => setAddingTask(false)} variant="outline" size="sm">
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </div>
          )}
          
          {tasks.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No tasks found. Tasks will be generated when you create a project.
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <div
                  key={task.task_id}
                  className="flex items-start gap-3 p-4 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  {editingTask === task.task_id ? (
                    <div className="flex-1 space-y-2">
                      <Input
                        placeholder="Task Number"
                        value={editedTask?.checklist_task_id}
                        onChange={(e) => setEditedTask({ ...editedTask!, checklist_task_id: e.target.value })}
                      />
                      <Input
                        placeholder="Description"
                        value={editedTask?.description}
                        onChange={(e) => setEditedTask({ ...editedTask!, description: e.target.value })}
                      />
                      <Input
                        type="date"
                        value={editedTask?.projected_date}
                        onChange={(e) => setEditedTask({ ...editedTask!, projected_date: e.target.value })}
                      />
                      <div className="flex gap-2">
                        <Button onClick={handleEditTask} size="sm">
                          <Save className="h-4 w-4 mr-2" />
                          Save
                        </Button>
                        <Button onClick={() => { setEditingTask(null); setEditedTask(null); }} variant="outline" size="sm">
                          <X className="h-4 w-4 mr-2" />
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <Checkbox
                        checked={!!task.actual_date}
                        onCheckedChange={() => toggleTask(task)}
                        className="mt-1"
                      />
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">
                            {task.checklist_task_id}
                          </span>
                      {task.required && (
                        <Badge variant="outline" className="text-xs">Required</Badge>
                      )}
                    </div>
                    <p className={`${task.actual_date ? "line-through text-muted-foreground" : ""}`}>
                      {task.description}
                    </p>
                    {task.notes && (
                      <p className="text-sm text-muted-foreground italic">
                        Note: {task.notes}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <label className="text-muted-foreground">Projected:</label>
                        <Input
                          type="date"
                          defaultValue={/^\d{4}-\d{2}-\d{2}$/.test(task.projected_date) ? task.projected_date : ''}
                          onBlur={(e) => updateTaskDate(task, 'projected_date', e.target.value)}
                          className="h-8 w-40"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="text-muted-foreground">Actual:</label>
                        <Input
                          type="date"
                          defaultValue={/^\d{4}-\d{2}-\d{2}$/.test(task.actual_date) ? task.actual_date : ''}
                          onBlur={(e) => updateTaskDate(task, 'actual_date', e.target.value)}
                          className="h-8 w-40"
                        />
                      </div>
                    </div>
                  </div>
                  {editMode && (
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingTask(task.task_id);
                          setEditedTask(task);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteTask(task.task_id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  )}
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
