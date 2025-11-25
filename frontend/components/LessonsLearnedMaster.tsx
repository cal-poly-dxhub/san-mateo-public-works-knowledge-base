"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiRequest } from "@/lib/api";
import MasterConflictsSection from "@/components/MasterConflictsSection";

interface Lesson {
  id: string;
  title: string;
  dateEntered: string;
  lesson: string;
  details: string;
  impact: string;
  recommendation: string;
  severity: "High" | "Medium" | "Low";
  projectName: string;
}

interface ProjectType {
  type: string;
  count: number;
  projects: string[];
}

export default function LessonsLearnedMaster() {
  const [projectTypes, setProjectTypes] = useState<ProjectType[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [editingLesson, setEditingLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjectTypes();
  }, []);

  const loadProjectTypes = async () => {
    try {
      const data = await apiRequest("/lessons/project-types");
      setProjectTypes(data.projectTypes || []);
    } catch (error) {
      console.error("Error loading project types:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadLessonsForType = async (projectType: string) => {
    try {
      setLoading(true);
      const data = await apiRequest(`/lessons/by-type/${encodeURIComponent(projectType)}`);
      setLessons(data.lessons || []);
      setSelectedType(projectType);
    } catch (error) {
      console.error("Error loading lessons:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveLesson = async (lesson: Lesson) => {
    try {
      await apiRequest(`/lessons/${lesson.id}`, {
        method: "PUT",
        body: JSON.stringify(lesson),
      });
      
      // Reload lessons for current type
      if (selectedType) {
        await loadLessonsForType(selectedType);
      }
      setEditingLesson(null);
    } catch (error) {
      console.error("Error saving lesson:", error);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "High": return "bg-red-100 text-red-800";
      case "Medium": return "bg-yellow-100 text-yellow-800";
      case "Low": return "bg-green-100 text-green-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  if (loading && !selectedType) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">Loading project types...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Lessons Learned by Project Type</CardTitle>
            {selectedType && (
              <Button variant="outline" onClick={() => setSelectedType(null)}>
                Back to Project Types
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!selectedType ? (
            // Project Types List
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projectTypes.map((projectType) => (
                <Card 
                  key={projectType.type} 
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => loadLessonsForType(projectType.type)}
                >
                  <CardContent className="p-4">
                    <h3 className="font-semibold">{projectType.type}</h3>
                    <div className="text-xs text-muted-foreground mt-2">
                      {projectType.projects?.slice(0, 3).join(", ") || ""}
                      {(projectType.projects?.length || 0) > 3 && "..."}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            // Lessons List for Selected Type
            <div className="space-y-4">
              <MasterConflictsSection projectType={selectedType} onResolved={() => loadLessonsForType(selectedType)} />
              
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">{selectedType} - Lessons Learned</h3>
                <Badge variant="outline">{lessons.length} lessons</Badge>
              </div>
              
              {loading ? (
                <div className="text-center text-muted-foreground py-8">Loading lessons...</div>
              ) : lessons.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">No lessons found for this project type.</div>
              ) : (
                <div className="space-y-3">
                  {lessons
                    .sort((a, b) => {
                      const severityOrder = { High: 0, Medium: 1, Low: 2 };
                      return severityOrder[a.severity] - severityOrder[b.severity];
                    })
                    .map((lesson, index) => (
                      <Card key={`${lesson.id}-${index}`} className="hover:bg-muted/50 transition-colors">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <Badge className={getSeverityColor(lesson.severity)}>
                                  {lesson.severity}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                  {lesson.projectName} • {lesson.dateEntered}
                                </span>
                              </div>
                              <h4 className="font-semibold mb-2">{lesson.title}</h4>
                              <p className="text-sm mb-2">{lesson.lesson}</p>
                              {lesson.details && (
                                <p className="text-sm text-muted-foreground mb-2">
                                  <strong>Details:</strong> {lesson.details}
                                </p>
                              )}
                              {lesson.impact && (
                                <p className="text-sm text-muted-foreground mb-2">
                                  <strong>Impact:</strong> {lesson.impact}
                                </p>
                              )}
                              {lesson.recommendation && (
                                <p className="text-sm text-muted-foreground">
                                  <strong>Recommendation:</strong> {lesson.recommendation}
                                </p>
                              )}
                            </div>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => setEditingLesson(lesson)}
                            >
                              Edit
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Lesson Dialog */}
      {editingLesson && (
        <Dialog open={!!editingLesson} onOpenChange={() => setEditingLesson(null)}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Lesson Learned</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Title</label>
                <Input
                  value={editingLesson.title}
                  onChange={(e) => setEditingLesson({...editingLesson, title: e.target.value})}
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Severity</label>
                <select
                  value={editingLesson.severity}
                  onChange={(e) => setEditingLesson({...editingLesson, severity: e.target.value as "High" | "Medium" | "Low"})}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Lesson</label>
                <Textarea
                  value={editingLesson.lesson}
                  onChange={(e) => setEditingLesson({...editingLesson, lesson: e.target.value})}
                  rows={3}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Details</label>
                <Textarea
                  value={editingLesson.details}
                  onChange={(e) => setEditingLesson({...editingLesson, details: e.target.value})}
                  rows={3}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Impact</label>
                <Textarea
                  value={editingLesson.impact}
                  onChange={(e) => setEditingLesson({...editingLesson, impact: e.target.value})}
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Recommendation</label>
                <Textarea
                  value={editingLesson.recommendation}
                  onChange={(e) => setEditingLesson({...editingLesson, recommendation: e.target.value})}
                  rows={2}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setEditingLesson(null)}>
                  Cancel
                </Button>
                <Button onClick={() => saveLesson(editingLesson)}>
                  Save Changes
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
