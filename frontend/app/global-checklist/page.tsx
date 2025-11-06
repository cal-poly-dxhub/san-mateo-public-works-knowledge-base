"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Plus, Trash2, Save, RefreshCw, Pencil } from "lucide-react";
import { apiRequest } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Task {
  task_id: string;
  description: string;
  required: boolean;
  notes: string;
  projected_date: string;
}

export default function GlobalChecklistPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [originalTasks, setOriginalTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [syncConfirmOpen, setSyncConfirmOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [checklistType, setChecklistType] = useState<"design" | "construction">("design");

  // Listen for changes from header toggle
  useEffect(() => {
    const handleChecklistTypeChange = (event: CustomEvent) => {
      setChecklistType(event.detail);
    };
    
    // Get initial value from localStorage
    const stored = localStorage.getItem('checklistType') as "design" | "construction";
    if (stored) setChecklistType(stored);
    
    window.addEventListener('checklistTypeChange', handleChecklistTypeChange as EventListener);
    return () => window.removeEventListener('checklistTypeChange', handleChecklistTypeChange as EventListener);
  }, []);

  const hasChanges = JSON.stringify(tasks) !== JSON.stringify(originalTasks);
  const [originalTask, setOriginalTask] = useState<Task | null>(null);

  useEffect(() => {
    loadChecklist();
  }, [checklistType]);

  const loadChecklist = async () => {
    setLoading(true);
    try {
      const data = await apiRequest(`/global-checklist?type=${checklistType}`);
      setTasks(data.tasks || []);
      setOriginalTasks(data.tasks || []);
    } catch (error) {
      console.error("Error loading checklist:", error);
    } finally {
      setLoading(false);
    }
  };

  const addTask = (afterTaskId?: string) => {
    const newTask: Task = {
      task_id: "",
      description: "",
      required: true,
      notes: "",
      projected_date: ""
    };
    
    if (afterTaskId) {
      const index = tasks.findIndex(t => t.task_id === afterTaskId);
      const newTasks = [...tasks];
      newTasks.splice(index + 1, 0, newTask);
      setTasks(newTasks);
      setEditingIndex(index + 1);
    } else {
      setTasks([...tasks, newTask]);
      setEditingIndex(tasks.length);
    }
  };

  const confirmTask = (index: number) => {
    const task = tasks[index];
    
    // Validate task_id
    if (!task.task_id) {
      alert("Task ID is required");
      return;
    }
    
    // Check for duplicates
    const duplicateExists = tasks.some((t, i) => i !== index && t.task_id === task.task_id);
    if (duplicateExists) {
      alert(`Task ID "${task.task_id}" already exists. Please use a unique ID.`);
      return;
    }
    
    // Sort tasks
    const newTasks = [...tasks];
    newTasks.sort((a, b) => {
      const aParts = a.task_id.split(".").map(n => parseInt(n) || 0);
      const bParts = b.task_id.split(".").map(n => parseInt(n) || 0);
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        const aVal = aParts[i] || 0;
        const bVal = bParts[i] || 0;
        if (aVal !== bVal) return aVal - bVal;
      }
      return 0;
    });
    
    setTasks(newTasks);
    setEditingIndex(null);
  };

  const cancelTask = (index: number) => {
    const task = tasks[index];
    if (!task.task_id && !task.description) {
      // Remove empty task
      setTasks(tasks.filter((_, i) => i !== index));
    }
    setEditingIndex(null);
  };

  const deleteTask = (taskId: string) => {
    setTasks(tasks.filter(t => t.task_id !== taskId));
  };

  const updateTask = (index: number, field: keyof Task, value: any) => {
    const newTasks = [...tasks];
    newTasks[index] = { ...newTasks[index], [field]: value };
    setTasks(newTasks);
  };

  const handleSave = () => {
    setConfirmOpen(true);
  };

  const confirmSave = async () => {
    setSaving(true);
    try {
      await apiRequest(`/global-checklist?type=${checklistType}`, {
        method: "PUT",
        body: JSON.stringify({ tasks })
      });
      setOriginalTasks([...tasks]);
      alert("Global checklist updated successfully");
      setConfirmOpen(false);
    } catch (error) {
      console.error("Error saving checklist:", error);
      alert("Error saving checklist");
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    // Save first
    setSaving(true);
    try {
      await apiRequest(`/global-checklist?type=${checklistType}`, {
        method: "PUT",
        body: JSON.stringify({ tasks })
      });
      setOriginalTasks([...tasks]);
      setSaving(false);
      // Then sync
      setSyncConfirmOpen(true);
    } catch (error) {
      console.error("Error saving checklist:", error);
      alert("Error saving checklist before sync");
      setSaving(false);
    }
  };

  const confirmSync = async () => {
    setSyncing(true);
    try {
      const result = await apiRequest("/global-checklist/sync", {
        method: "POST"
      });
      alert(`Synced successfully: ${result.message}`);
      setSyncConfirmOpen(false);
    } catch (error) {
      console.error("Error syncing:", error);
      alert("Error syncing to projects");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Global {checklistType.charAt(0).toUpperCase() + checklistType.slice(1)} Checklist</h1>
            <p className="text-muted-foreground mt-2">
              {tasks.length} tasks • Edit in place, add tasks between items
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleSync} disabled={syncing}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Sync to All Projects
            </Button>
            {hasChanges && (
              <Button onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-2">
          {tasks.map((task, index) => (
            <div key={index} className="border rounded-lg p-3 bg-card hover:bg-accent/50 transition-colors">
              {editingIndex === index ? (
                <div className="flex gap-3 items-start">
                  <Input
                    value={task.task_id}
                    onChange={(e) => updateTask(index, "task_id", e.target.value)}
                    placeholder="ID"
                    className="w-20"
                  />
                  <Textarea
                    value={task.description}
                    onChange={(e) => updateTask(index, "description", e.target.value)}
                    placeholder="Task description"
                    rows={2}
                    className="flex-1"
                  />
                  <Input
                    value={task.notes}
                    onChange={(e) => updateTask(index, "notes", e.target.value)}
                    placeholder="Notes"
                    className="w-48"
                  />
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={task.required}
                      onCheckedChange={(checked) => updateTask(index, "required", !!checked)}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => confirmTask(index)}
                      title="Confirm task"
                    >
                      <Save className="h-4 w-4 text-green-500" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelTask(index)}
                      title="Cancel"
                    >
                      <Trash2 className="h-4 w-4 text-gray-500" />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-3 items-center">
                  <div className="w-20 font-mono text-sm">{task.task_id}</div>
                  <div className="flex-1 text-sm">{task.description}</div>
                  <div className="w-48 text-sm text-muted-foreground">{task.notes}</div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={task.required}
                      disabled
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingIndex(index)}
                      title="Edit task"
                      disabled={editingIndex !== null}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => addTask(task.task_id)}
                      title="Add task below"
                      disabled={editingIndex !== null}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteTask(task.task_id)}
                      disabled={editingIndex !== null}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <Button onClick={() => addTask()} className="mt-4" variant="outline" disabled={editingIndex !== null}>
          <Plus className="h-4 w-4 mr-2" />
          Add Task at End
        </Button>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Changes</DialogTitle>
            <DialogDescription>
              Are you sure you want to save these changes to the global checklist?
              This will affect all future projects created from this checklist.
              Existing projects will NOT be automatically updated until you click "Sync to All Projects".
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmSave} disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={syncConfirmOpen} onOpenChange={setSyncConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sync to All Projects</DialogTitle>
            <DialogDescription>
              This will update ALL existing projects with the current global checklist.
              Only unchecked tasks will be updated. Completed tasks will remain unchanged.
              Tasks deleted from the global checklist will be removed from projects (if unchecked).
              New tasks will be added to all projects.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncConfirmOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmSync} disabled={syncing} variant="destructive">
              {syncing ? "Syncing..." : "Sync Now"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
