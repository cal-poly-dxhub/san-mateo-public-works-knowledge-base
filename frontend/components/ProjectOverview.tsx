"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, FileText, MessageSquare, Target, Calendar } from "lucide-react";

interface ProjectOverviewData {
  projectName: string;
  description: string;
  teamMembers: string[];
  timeline?: {
    startDate: string;
    endDate: string;
  };
  goals?: string[];
  customerRequirements?: string[];
  notes?: string;
}

interface ProjectOverviewProps {
  overviewData: ProjectOverviewData | null;
}

export default function ProjectOverview({ overviewData }: ProjectOverviewProps) {
  if (!overviewData) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">No project overview available</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Project Description */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Project Description
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">{overviewData.description}</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Team Members */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Team Members ({overviewData.teamMembers.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {overviewData.teamMembers.map((member, index) => (
                <Badge key={index} variant="secondary" className="mr-2 mb-2">
                  {member}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Customer Requirements/Goals */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Requirements & Goals ({(overviewData.goals || overviewData.customerRequirements || []).length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(overviewData.goals || overviewData.customerRequirements || []).length > 0 ? (
              <ul className="space-y-2">
                {(overviewData.goals || overviewData.customerRequirements || []).map((item, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-primary font-medium text-sm mt-0.5">•</span>
                    <span className="text-sm leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No requirements or goals defined</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
