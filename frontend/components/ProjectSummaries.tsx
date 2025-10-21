"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface TimelineItem {
  item_id: string;
  item_type: "meeting" | "action_item";
  date: string;
  meeting_type?: string;
  filename?: string;
  summary?: {
    overview?: string;
    participants?: string[];
    key_points?: string[];
    direct_quotes?: string[];
    next_steps?: string[];
  };
}

interface ProjectSummariesProps {
  projectName: string;
}

export default function ProjectSummaries({ projectName }: ProjectSummariesProps) {
  const [meetings, setMeetings] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedSummaries, setExpandedSummaries] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchMeetings();
  }, [projectName]);

  const fetchMeetings = async () => {
    try {
      const response = await apiRequest(`/projects/${projectName}/timeline`);
      const meetingsOnly = (response.timeline || []).filter(item => item.item_type === "meeting");
      setMeetings(meetingsOnly);
    } catch (error) {
      console.error("Error fetching meetings:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSummary = (meetingId: string) => {
    setExpandedSummaries(prev => {
      const newSet = new Set(prev);
      if (newSet.has(meetingId)) {
        newSet.delete(meetingId);
      } else {
        newSet.add(meetingId);
      }
      return newSet;
    });
  };

  if (loading) {
    return <div className="text-center py-8">Loading summaries...</div>;
  }

  if (meetings.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No meeting summaries available
      </div>
    );
  }

  const sortedMeetings = meetings.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  return (
    <div className="space-y-4">
      {sortedMeetings.map((meeting) => (
        <div key={meeting.item_id} className="bg-card border rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-lg">
                {meeting.meeting_type} Meeting
              </h3>
              <p className="text-sm text-muted-foreground">
                {new Date(meeting.date).toLocaleDateString()} • {meeting.filename}
              </p>
            </div>
            <button
              onClick={() => toggleSummary(meeting.item_id)}
              className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 rounded text-blue-700"
            >
              {expandedSummaries.has(meeting.item_id) ? "Hide" : "Show"} Summary
              {expandedSummaries.has(meeting.item_id) ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          </div>
          
          {meeting.summary && expandedSummaries.has(meeting.item_id) && (
            <div className="p-4 bg-gray-50 rounded border">
              {meeting.summary.overview && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Overview</h4>
                  <p className="text-sm text-gray-600 leading-relaxed">{meeting.summary.overview}</p>
                </div>
              )}
              
              {meeting.summary.participants && meeting.summary.participants.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Participants</h4>
                  <div className="flex flex-wrap gap-1">
                    {meeting.summary.participants.map((participant, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {participant}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              {meeting.summary.key_points && meeting.summary.key_points.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Key Points</h4>
                  <ul className="text-sm text-gray-600 space-y-2">
                    {meeting.summary.key_points.map((point, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-500 mt-1 font-bold">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {meeting.summary.direct_quotes && meeting.summary.direct_quotes.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Direct Quotes</h4>
                  <div className="space-y-3">
                    {meeting.summary.direct_quotes.map((quote, idx) => (
                      <blockquote key={idx} className="text-sm text-gray-600 italic border-l-4 border-blue-300 pl-4 py-2 bg-blue-50">
                        "{quote}"
                      </blockquote>
                    ))}
                  </div>
                </div>
              )}
              
              {meeting.summary.next_steps && meeting.summary.next_steps.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Next Steps</h4>
                  <ul className="text-sm text-gray-600 space-y-2">
                    {meeting.summary.next_steps.map((step, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-500 mt-1 font-bold">→</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          
          {!meeting.summary && (
            <div className="text-center py-4 text-muted-foreground text-sm">
              No summary available for this meeting
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
