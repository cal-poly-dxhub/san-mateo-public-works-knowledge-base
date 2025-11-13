export interface Lesson {
  id: string;
  title: string;
  lesson: string;
  impact: string;
  recommendation: string;
  severity: "High" | "Medium" | "Low";
  source_document?: string;
  projectName?: string;
  projectType?: string;
  created_at?: string;
}

export interface Conflict {
  id: string;
  new_lesson: Lesson;
  existing_lesson: Lesson;
  conflict_type: string;
  similarity_score: number;
  analysis: string;
  status: "pending" | "resolved";
  decision?: string;
}

export interface LessonsData {
  projectType?: string;
  projectName?: string;
  lastUpdated: string;
  lessons: Lesson[];
}
