"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GripVertical, ChevronDown, ChevronUp } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface TimelineItem {
  item_id: string;
  item_type: "meeting" | "action_item";
  date: string;
  meeting_type?: string;
  filename?: string;
  title?: string;
  assignee?: string;
  action_status?: string;
  meeting_item_id?: string;
  summary?: {
    overview?: string;
    participants?: string[];
    key_points?: string[];
    direct_quotes?: string[];
    next_steps?: string[];
  };
}

interface MeetingSummary {
  overview?: string;
  participants?: string[];
  key_points?: string[];
  direct_quotes?: string[];
  next_steps?: string[];
}

interface ProjectTimelineProps {
  projectName: string;
}

export default function ProjectTimeline({ projectName }: ProjectTimelineProps) {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({
    title: "",
    assignee: "",
    action_status: "",
  });
  const [draggedItem, setDraggedItem] = useState<TimelineItem | null>(null);
  const [expandedSummaries, setExpandedSummaries] = useState<Set<string>>(new Set());
  const [loadedSummaries, setLoadedSummaries] = useState<Map<string, MeetingSummary>>(new Map());
  const [loadingSummaries, setLoadingSummaries] = useState<Set<string>>(new Set());


  useEffect(() => {
    fetchTimeline();
  }, [projectName]);

  const fetchTimeline = async () => {
    try {
      const response = await apiRequest(`/projects/${projectName}/timeline`);
      setTimeline(response.timeline || []);
    } catch (error) {
      console.error("Error fetching timeline:", error);
    } finally {
      setLoading(false);
    }
  };

  const createActionItem = async (meeting: any) => {
    try {
      if (!editForm.title.trim()) {
        alert("Please enter a title for the action item");
        return;
      }

      await apiRequest(`/projects/${projectName}/action-items`, {
        method: "POST",
        body: JSON.stringify({
          title: editForm.title,
          assignee: editForm.assignee || "",
          action_status: editForm.action_status || "open",
          meeting_uuid: meeting.filename, // Use filename as meeting identifier
          meeting_date: meeting.date,
        }),
      });

      await fetchTimeline();
      setEditingItem(null);
      setEditForm({ title: "", assignee: "", action_status: "open" });
    } catch (error) {
      console.error("Error creating action item:", error);
      alert(`Error creating action item: ${error}`);
    }
  };

  const updateActionItem = async (
    itemId: string,
    updates: any,
    isInlineEdit = false,
  ) => {
    try {
      // Optimistic update for inline edits
      if (isInlineEdit) {
        setTimeline((prev) =>
          prev.map((item) =>
            item.item_id === itemId ? { ...item, ...updates } : item,
          ),
        );
      }

      const encodedId = encodeURIComponent(itemId);
      const response = await apiRequest(
        `/projects/${projectName}/action-items/${encodedId}`,
        {
          method: "PUT",
          body: JSON.stringify(updates),
        },
      );

      if (!isInlineEdit) {
        setEditingItem(null);
      }
    } catch (error) {
      console.error("Error updating action item:", error);
      // Revert on error
      if (isInlineEdit) {
        await fetchTimeline();
      }
      alert(`Error updating action item: ${error}`);
    }
  };

  const handleDragStart = (e: React.DragEvent, item: TimelineItem) => {
    setDraggedItem(item);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = async (e: React.DragEvent, targetMeetingId: string) => {
    e.preventDefault();
    if (!draggedItem) return;

    // Don't update if dropping on same meeting
    if (targetMeetingId === draggedItem.meeting_item_id) {
      setDraggedItem(null);
      return;
    }

    // Validate that we have required data
    if (!draggedItem.item_id || !targetMeetingId) {
      console.error("Missing required data for drag and drop");
      setDraggedItem(null);
      return;
    }

    // Optimistic update - update UI immediately
    setTimeline((prev) =>
      prev.map((item) =>
        item.item_id === draggedItem.item_id
          ? { ...item, meeting_item_id: targetMeetingId }
          : item,
      ),
    );

    setDraggedItem(null);

    // Then update backend
    try {
      await updateActionItem(draggedItem.item_id, {
        meeting_item_id: targetMeetingId,
      });
    } catch (error) {
      console.error("Error in drag and drop:", error);
      // Revert on error
      await fetchTimeline();
    }
  };

  const deleteActionItem = async (itemId: string) => {
    try {
      // Optimistic update - remove from UI immediately
      setTimeline((prev) => prev.filter((item) => item.item_id !== itemId));

      const encodedId = encodeURIComponent(itemId);
      const response = await apiRequest(
        `/projects/${projectName}/action-items/${encodedId}`,
        {
          method: "DELETE",
        },
      );
    } catch (error) {
      console.error("Error deleting action item:", error);
      // Revert on error
      await fetchTimeline();
      alert(`Error deleting action item: ${error}`);
    }
  };

  const fetchSummary = async (meetingId: string) => {
    if (loadedSummaries.has(meetingId) || loadingSummaries.has(meetingId)) {
      return;
    }

    setLoadingSummaries(prev => new Set(prev).add(meetingId));
    
    try {
      const encodedMeetingId = encodeURIComponent(meetingId);
      const response = await apiRequest(`/projects/${projectName}/meetings/${encodedMeetingId}/summary`);
      setLoadedSummaries(prev => new Map(prev).set(meetingId, response.summary));
    } catch (error) {
      console.error("Error fetching summary:", error);
    } finally {
      setLoadingSummaries(prev => {
        const newSet = new Set(prev);
        newSet.delete(meetingId);
        return newSet;
      });
    }
  };

  const toggleSummary = async (meetingId: string) => {
    const isExpanding = !expandedSummaries.has(meetingId);
    
    setExpandedSummaries(prev => {
      const newSet = new Set(prev);
      if (newSet.has(meetingId)) {
        newSet.delete(meetingId);
      } else {
        newSet.add(meetingId);
      }
      return newSet;
    });

    if (isExpanding && !loadedSummaries.has(meetingId)) {
      await fetchSummary(meetingId);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading timeline...</div>;
  }

  if (timeline.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No meetings or action items available
      </div>
    );
  }

  // Sort timeline by date
  const sortedTimeline = timeline.sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  );

  // Group timeline items by meetings and their action items
  // First, create groups for all meetings
  const meetings = sortedTimeline.filter(item => item.item_type === "meeting");
  const actionItems = sortedTimeline.filter(item => item.item_type === "action_item");
  
  const groupedTimeline = meetings.map(meeting => ({
    meeting,
    actionItems: [] as TimelineItem[]
  }));
  
  // Then, assign action items to their respective meetings
  actionItems.forEach(item => {
    const targetMeetingId = item.meeting_item_id;
    const meetingIndex = groupedTimeline.findIndex(
      (group) => group.meeting.item_id === targetMeetingId,
    );

    if (meetingIndex >= 0) {
      groupedTimeline[meetingIndex].actionItems.push(item);
    } else if (groupedTimeline.length > 0) {
      // If no meeting match found, add to the most recent meeting
      groupedTimeline[groupedTimeline.length - 1].actionItems.push(item);
    } else {
      // If no meetings exist, create a standalone action items group
      groupedTimeline.push({
        meeting: null,
        actionItems: [item],
      });
    }
  });

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-border"></div>

      <div className="space-y-12">
        {(groupedTimeline as Array<{ meeting: TimelineItem | null; actionItems: TimelineItem[] }>).map((group, groupIndex) => (
          <div
            key={group.meeting?.item_id || `actions-${groupIndex}`}
            className="relative"
          >
            {/* Meeting node (if meeting exists) */}
            {group.meeting && (
              <div className="flex items-start">
                <div className="relative z-10 flex items-center justify-center w-16 h-16 bg-primary text-primary-foreground rounded-full border-4 border-background shadow-lg">
                  <span className="text-sm font-bold">M</span>
                </div>
                <div className="ml-6 flex-1">
                  <div className="bg-card border rounded-lg p-4 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-lg">
                        {group.meeting.meeting_type} Meeting
                      </h3>
                      <button
                        onClick={() => toggleSummary(group.meeting.item_id)}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-700"
                        disabled={loadingSummaries.has(group.meeting.item_id)}
                      >
                        {loadingSummaries.has(group.meeting.item_id) ? 'Loading...' : 'Summary'}
                        {expandedSummaries.has(group.meeting.item_id) ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {new Date(group.meeting.date).toLocaleDateString()}
                    </p>
                    <p className="text-sm">{group.meeting.filename}</p>
                    
                    {/* Summary dropdown */}
                    {expandedSummaries.has(group.meeting.item_id) && (
                      <div className="mt-4 p-3 bg-gray-50 rounded border">
                        {(() => {
                          const summary = loadedSummaries.get(group.meeting.item_id);
                          const isLoading = loadingSummaries.has(group.meeting.item_id);
                          
                          if (isLoading) {
                            return <div className="text-sm text-gray-500">Loading...</div>;
                          }
                          
                          if (!summary) {
                            return <div className="text-sm text-gray-500">No summary available</div>;
                          }
                          
                          return (
                            <>
                              {summary.overview && (
                                <div className="mb-3">
                                  <h4 className="text-sm font-medium text-gray-700 mb-1">Overview</h4>
                                  <p className="text-sm text-gray-600">{summary.overview}</p>
                                </div>
                              )}
                              
                              {summary.participants && summary.participants.length > 0 && (
                                <div className="mb-3">
                                  <h4 className="text-sm font-medium text-gray-700 mb-1">Participants</h4>
                                  <div className="flex flex-wrap gap-1">
                                    {summary.participants.map((participant, idx) => (
                                      <Badge key={idx} variant="secondary" className="text-xs">
                                        {participant}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {summary.key_points && summary.key_points.length > 0 && (
                                <div className="mb-3">
                                  <h4 className="text-sm font-medium text-gray-700 mb-1">Key Points</h4>
                                  <ul className="text-sm text-gray-600 space-y-1">
                                    {summary.key_points.map((point, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <span className="text-blue-500 mt-1">•</span>
                                        <span>{point}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              
                              {summary.direct_quotes && summary.direct_quotes.length > 0 && (
                                <div className="mb-3">
                                  <h4 className="text-sm font-medium text-gray-700 mb-1">Direct Quotes</h4>
                                  <div className="space-y-2">
                                    {summary.direct_quotes.map((quote, idx) => (
                                      <blockquote key={idx} className="text-sm text-gray-600 italic border-l-2 border-gray-300 pl-3">
                                        "{quote}"
                                      </blockquote>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {summary.next_steps && summary.next_steps.length > 0 && (
                                <div>
                                  <h4 className="text-sm font-medium text-gray-700 mb-1">Next Steps</h4>
                                  <ul className="text-sm text-gray-600 space-y-1">
                                    {summary.next_steps.map((step, idx) => (
                                      <li key={idx} className="flex items-start gap-2">
                                        <span className="text-green-500 mt-1">→</span>
                                        <span>{step}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Action items for this meeting */}
            {(group.actionItems.length > 0 || group.meeting) && (
              <div
                className={`${group.meeting ? "ml-24 mt-4 space-y-2" : "ml-0 space-y-2"} min-h-[60px] border-2 border-dashed border-transparent hover:border-blue-300 transition-colors rounded p-2`}
                onDragOver={handleDragOver}
                onDrop={(e) =>
                  handleDrop(e, group.meeting?.item_id || "unassigned")
                }
              >
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-muted-foreground">
                    {group.meeting ? "Action Items:" : "Action Items"}
                  </h4>
                  {group.meeting && (
                    <button
                      className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-700"
                      onClick={() => {
                        const meetingKey = `${group.meeting.filename}-${group.meeting.date}`;
                        setEditingItem(`new-${meetingKey}`);
                        setEditForm({
                          title: "",
                          assignee: "",
                          action_status: "open",
                        });
                      }}
                    >
                      + Add Item
                    </button>
                  )}
                </div>
                {/* New action item form */}
                {editingItem ===
                  `new-${group.meeting?.filename}-${group.meeting?.date}` &&
                  group.meeting && (
                    <div className="p-3 rounded-lg border bg-blue-50 border-blue-200">
                      <div className="space-y-2">
                        <Input
                          value={editForm.title}
                          onChange={(e) =>
                            setEditForm({ ...editForm, title: e.target.value })
                          }
                          placeholder="Action item title"
                          className="text-sm"
                        />
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              Assigned:
                            </span>
                            <Input
                              value={editForm.assignee}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  assignee: e.target.value,
                                })
                              }
                              placeholder="Enter name"
                              className="h-7 text-xs w-24"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              Status:
                            </span>
                            <Select
                              value={editForm.action_status}
                              onValueChange={(value) =>
                                setEditForm({
                                  ...editForm,
                                  action_status: value,
                                })
                              }
                            >
                              <SelectTrigger className="h-7 text-xs w-28">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="open">Open</SelectItem>
                                <SelectItem value="in-progress">
                                  In Progress
                                </SelectItem>
                                <SelectItem value="completed">
                                  Completed
                                </SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex gap-2 ml-auto">
                            <button
                              className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded"
                              onClick={() => createActionItem(group.meeting)}
                            >
                              Create
                            </button>
                            <button
                              className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                              onClick={() => setEditingItem(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                {/* Sort action items by status only */}
                {group.actionItems
                  .sort((a, b) => {
                    // Sort by status: open -> in-progress -> completed
                    const statusOrder = {
                      open: 0,
                      "in-progress": 1,
                      completed: 2,
                    };
                    return (
                      (statusOrder[a.action_status] || 0) -
                      (statusOrder[b.action_status] || 0)
                    );
                  })
                  .map((actionItem) => {
                    const isCompleted =
                      actionItem.action_status === "completed";
                    const statusColors = {
                      open: "bg-red-50 border-red-200",
                      "in-progress": "bg-yellow-50 border-yellow-200",
                      completed: "bg-green-50 border-green-200",
                    };
                    const statusColor =
                      statusColors[actionItem.action_status] ||
                      statusColors["open"];

                    return (
                      <div
                        key={actionItem.item_id}
                        className={`p-3 rounded-lg border ${statusColor} ${isCompleted ? "opacity-75" : ""} cursor-move`}
                        draggable
                        onDragStart={(e) => handleDragStart(e, actionItem)}
                      >
                        {editingItem === actionItem.item_id ? (
                          // Edit mode
                          <div className="space-y-2">
                            <Input
                              value={editForm.title}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  title: e.target.value,
                                })
                              }
                              placeholder="Action item title"
                              className="text-sm"
                            />
                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">
                                  Assigned:
                                </span>
                                <Input
                                  value={editForm.assignee}
                                  onChange={(e) =>
                                    setEditForm({
                                      ...editForm,
                                      assignee: e.target.value,
                                    })
                                  }
                                  placeholder="Enter name"
                                  className="h-7 text-xs w-24"
                                />
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">
                                  Status:
                                </span>
                                <Select
                                  value={editForm.action_status}
                                  onValueChange={(value) =>
                                    setEditForm({
                                      ...editForm,
                                      action_status: value,
                                    })
                                  }
                                >
                                  <SelectTrigger className="h-7 text-xs w-28">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="open">Open</SelectItem>
                                    <SelectItem value="in-progress">
                                      In Progress
                                    </SelectItem>
                                    <SelectItem value="completed">
                                      Completed
                                    </SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="flex gap-2 ml-auto">
                                <button
                                  className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded"
                                  onClick={() =>
                                    updateActionItem(
                                      actionItem.item_id,
                                      editForm,
                                    )
                                  }
                                >
                                  Save
                                </button>
                                <button
                                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                                  onClick={() => setEditingItem(null)}
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          </div>
                        ) : (
                          // Display mode - single line layout
                          <div className="flex items-center gap-3">
                            {/* Drag Handle */}
                            <div className="flex items-center justify-center w-6 h-6 rounded">
                              <GripVertical className="h-4 w-4 text-gray-600" />
                            </div>

                            {/* Title */}
                            <div className="flex-1">
                              <span
                                className={`text-sm font-medium ${isCompleted ? "line-through text-gray-500" : ""}`}
                              >
                                {actionItem.title}
                              </span>
                            </div>

                            {/* Assignee (read-only display) */}
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-xs text-muted-foreground">
                                Assigned:
                              </span>
                              <span className="text-xs font-medium">
                                {actionItem.assignee || "Unassigned"}
                              </span>
                            </div>

                            {/* Status dropdown */}
                            <div className="flex items-center gap-2">
                              <Select
                                value={actionItem.action_status || "open"}
                                onValueChange={(value) => {
                                  updateActionItem(
                                    actionItem.item_id,
                                    { action_status: value },
                                    true,
                                  );
                                }}
                              >
                                <SelectTrigger className="h-7 text-xs w-28 border-0 bg-transparent">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="open">Open</SelectItem>
                                  <SelectItem value="in-progress">
                                    In Progress
                                  </SelectItem>
                                  <SelectItem value="completed">
                                    Completed
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>

                            {/* Action buttons */}
                            <div className="flex gap-1">
                              <button
                                className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  setEditingItem(actionItem.item_id);
                                  setEditForm({
                                    title: actionItem.title || "",
                                    assignee: actionItem.assignee || "",
                                    action_status:
                                      actionItem.action_status || "open",
                                  });
                                }}
                              >
                                Edit
                              </button>
                              <button
                                className="px-2 py-1 text-xs bg-red-100 hover:bg-red-200 rounded"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  deleteActionItem(actionItem.item_id);
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
