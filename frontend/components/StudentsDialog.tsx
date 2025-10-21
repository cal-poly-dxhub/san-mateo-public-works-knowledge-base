"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api-client";

interface Student {
  name: string;
  alias: string;
  seniority: string;
  strengths: string;
  skills: string;
  availability: string;
}

interface StudentsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function StudentsDialog({ open, onOpenChange }: StudentsDialogProps) {
  const { apiKey } = useApiKey();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      loadStudents();
    }
  }, [open]);

  const loadStudents = async () => {
    setLoading(true);
    try {
      const response = await apiRequest("/students", {}, apiKey);
      if (response.ok) {
        const data = await response.json();
        // Convert skills array to string for editing
        const studentsWithStringSkills = data.map((student: any) => ({
          ...student,
          skills: Array.isArray(student.skills) ? student.skills.join(", ") : student.skills || ""
        }));
        setStudents(studentsWithStringSkills);
      }
    } catch (error) {
      console.error("Error loading students:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveStudents = async () => {
    setSaving(true);
    try {
      // Convert skills string back to array before saving
      const studentsWithArraySkills = students.map(student => ({
        ...student,
        skills: student.skills.split(",").map(s => s.trim()).filter(Boolean)
      }));
      
      const response = await apiRequest(
        "/students",
        {
          method: "POST",
          body: JSON.stringify({ students: studentsWithArraySkills }),
        },
        apiKey
      );
      if (response.ok) {
        onOpenChange(false);
      }
    } catch (error) {
      console.error("Error saving students:", error);
    } finally {
      setSaving(false);
    }
  };

  const updateStudent = (index: number, field: keyof Student, value: string | string[]) => {
    const updated = [...students];
    updated[index] = { ...updated[index], [field]: value };
    setStudents(updated);
  };

  const addStudent = () => {
    setStudents([
      ...students,
      {
        name: "",
        alias: "",
        seniority: "junior",
        strengths: "",
        skills: "",
        availability: "full-time",
      },
    ]);
  };

  const removeStudent = (index: number) => {
    setStudents(students.filter((_, i) => i !== index));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Students</DialogTitle>
        </DialogHeader>
        
        {loading ? (
          <div className="text-center py-8">Loading students...</div>
        ) : (
          <div className="space-y-6">
            {students.map((student, index) => (
              <div key={index} className="border p-4 rounded-lg space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">Student {index + 1}</h3>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => removeStudent(index)}
                  >
                    Remove
                  </Button>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={student.name}
                      onChange={(e) => updateStudent(index, "name", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label>Alias</Label>
                    <Input
                      value={student.alias}
                      onChange={(e) => updateStudent(index, "alias", e.target.value)}
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Seniority</Label>
                    <Select
                      value={student.seniority}
                      onValueChange={(value) => updateStudent(index, "seniority", value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="junior">Junior</SelectItem>
                        <SelectItem value="intermediate">Intermediate</SelectItem>
                        <SelectItem value="senior">Senior</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Availability</Label>
                    <Select
                      value={student.availability}
                      onValueChange={(value) => updateStudent(index, "availability", value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="full-time">Full-time</SelectItem>
                        <SelectItem value="part-time">Part-time</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div>
                  <Label>Skills (comma-separated)</Label>
                  <Input
                    value={student.skills}
                    onChange={(e) => updateStudent(index, "skills", e.target.value)}
                  />
                </div>
                
                <div>
                  <Label>Strengths</Label>
                  <Textarea
                    value={student.strengths}
                    onChange={(e) => updateStudent(index, "strengths", e.target.value)}
                  />
                </div>
              </div>
            ))}
            
            <div className="flex justify-between">
              <Button variant="outline" onClick={addStudent}>
                Add Student
              </Button>
              <div className="space-x-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button onClick={saveStudents} disabled={saving}>
                  {saving ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
