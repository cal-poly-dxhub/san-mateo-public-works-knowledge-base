export interface Task {
  task_id: string;
  checklist_task_id: string;
  description: string;
  projected_date: string;
  actual_date: string;
  required: boolean;
  notes: string;
  status: string;
}

export interface Metadata {
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

export interface Project {
  name: string;
  type: string;
  status: string;
  created_at: string;
  updated_at: string;
  metadata?: Metadata;
}

export interface ProjectType {
  type: string;
  count: number;
  projects: string[];
}
