"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, GripVertical } from "lucide-react";
import { apiRequest } from "@/lib/api";

interface ActionItem {
  item_id: string;
  title: string;
  assignee?: string;
  action_status: string;
  date: string;
  created_from_meeting?: string;
  meeting_id?: string;
  order?: number;
}

interface Meeting {
  item_id: string;
  date: string;
  meeting_type: string;
  filename?: string;
}

interface ActionItemsProps {
  projectName: string;
}

export default function ActionItems({ projectName }: ActionItemsProps) {
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title: "", assignee: "", action_status: "" });
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({ title: "", assignee: "", action_status: "open" });
  const [draggedItem, setDraggedItem] = useState<ActionItem | null>(null);

  useEffect(() => {
    fetchData();
  }, [projectName]);

  const fetchData = async () => {
    try {
      const response = await apiRequest(`/projects/${projectName}/timeline`);
      const timeline = response.timeline || [];
      
      const items = timeline.filter((item: any) => item.item_type === "action_item");
      const meetingList = timeline.filter((item: any) => item.item_type === "meeting");
      
      setActionItems(items);
      setMeetings(meetingList);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateActionItem = async (itemId: string, updates: any) => {
    try {
      await apiRequest(`/projects/${projectName}/action-items/${itemId}`, {
        method: "PUT",
        body: JSON.stringify(updates),
      });
      fetchData();
      setEditingItem(null);
    } catch (error) {
      console.error("Error updating action item:", error);
    }
  };

  const updateActionItemOrder = async (itemId: string, newMeetingId: string, newOrder: number) => {
    try {
      await apiRequest(`/projects/${projectName}/action-items/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ meeting_id: newMeetingId, order: newOrder }),
      });
      fetchData();
    } catch (error) {
      console.error("Error updating action item order:", error);
    }
  };

  const deleteActionItem = async (itemId: string) => {
    try {
      await apiRequest(`/projects/${projectName}/action-items/${itemId}`, {
        method: "DELETE",
      });
      fetchData();
    } catch (error) {
      console.error("Error deleting action item:", error);
    }
  };

  const createActionItem = async () => {
    try {
      await apiRequest(`/projects/${projectName}/action-items`, {
        method: "POST",
        body: JSON.stringify(addForm),
      });
      fetchData();
      setShowAddForm(false);
      setAddForm({ title: "", assignee: "", action_status: "open" });
    } catch (error) {
      console.error("Error creating action item:", error);
    }
  };

  const handleDragStart = (e: React.DragEvent, item: ActionItem) => {
    setDraggedItem(item);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = (e: React.DragEvent, targetMeetingId: string, targetIndex?: number) => {
    e.preventDefault();
    if (!draggedItem) return;

    const targetMeetingItems = getActionItemsForMeeting(targetMeetingId);
    const newOrder = targetIndex !== undefined ? targetIndex : targetMeetingItems.length;
    
    updateActionItemOrder(draggedItem.item_id, targetMeetingId, newOrder);
    setDraggedItem(null);
  };

  const getActionItemsForMeeting = (meetingId: string) => {
    return actionItems
      .filter(item => item.meeting_id === meetingId || (!item.meeting_id && item.created_from_meeting === meetingId))
      .sort((a, b) => (a.order || 0) - (b.order || 0));
  };

  const getMeetingTitle = (meeting: Meeting) => {
    return meeting.filename || `${meeting.meeting_type} - ${new Date(meeting.date).toLocaleDateString()}`;
  };

  if (loading) {
    return <div className="text-center py-8">Loading action items...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Action Items</h3>
        <Button onClick={() => setShowAddForm(true)} size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Add Action Item
        </Button>
      </div>

      {showAddForm && (
        <Card>
          <CardHeader>
            <CardTitle>Add New Action Item</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              value={addForm.title}
              onChange={(e) => setAddForm({ ...addForm, title: e.target.value })}
              placeholder="Task description"
            />
            <Input
              value={addForm.assignee}
              onChange={(e) => setAddForm({ ...addForm, assignee: e.target.value })}
              placeholder="Assignee (optional)"
            />
            <Select
              value={addForm.action_status}
              onValueChange={(value) => setAddForm({ ...addForm, action_status: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="in-progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex gap-2">
              <Button onClick={createActionItem} disabled={!addForm.title.trim()}>
                Create
              </Button>
              <Button variant="outline" onClick={() => setShowAddForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {meetings.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No meetings found. Upload meeting recordings to see action items.
        </div>
      ) : (
        <div className="space-y-6">
          {meetings.map((meeting) => {
            const meetingActionItems = getActionItemsForMeeting(meeting.item_id);
            return (
              <Card key={meeting.item_id}>
                <CardHeader>
                  <CardTitle className="text-base">{getMeetingTitle(meeting)}</CardTitle>
                </CardHeader>
                <CardContent
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, meeting.item_id)}
                  className="space-y-3 min-h-[60px] border-2 border-dashed border-transparent hover:border-gray-300 transition-colors"
                >
                  {meetingActionItems.length === 0 ? (
                    <div className="text-sm text-muted-foreground py-4 text-center">
                      No action items. Drag items here or they will be auto-generated from meeting summaries.
                    </div>
                  ) : (
                    meetingActionItems.map((item, index) => (
                      <Card 
                        key={item.item_id}
                        className="hover:shadow-md transition-shadow"
                      >
                        <CardContent className="p-4">
                          {editingItem === item.item_id ? (
                            <div className="space-y-3">
                              <Input
                                value={editForm.title}
                                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                                placeholder="Task description"
                              />
                              <Input
                                value={editForm.assignee}
                                onChange={(e) => setEditForm({ ...editForm, assignee: e.target.value })}
                                placeholder="Assignee"
                              />
                              <Select
                                value={editForm.action_status}
                                onValueChange={(value) => setEditForm({ ...editForm, action_status: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="open">Open</SelectItem>
                                  <SelectItem value="in-progress">In Progress</SelectItem>
                                  <SelectItem value="completed">Completed</SelectItem>
                                </SelectContent>
                              </Select>
                              <div className="flex gap-2">
                                <Button size="sm" onClick={() => updateActionItem(item.item_id, editForm)}>
                                  Save
                                </Button>
                                <Button size="sm" variant="outline" onClick={() => setEditingItem(null)}>
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-start gap-3">
                              <div 
                                className="flex items-center justify-center w-6 h-6 cursor-grab hover:bg-gray-100 rounded active:cursor-grabbing"
                                draggable
                                onDragStart={(e) => handleDragStart(e, item)}
                              >
                                <GripVertical className="h-4 w-4 text-gray-600 hover:text-gray-800" />
                              </div>
                              <div className="flex-1">
                                <div className="flex justify-between items-start mb-2">
                                  <h4 className="font-medium">{item.title}</h4>
                                  <Badge
                                    variant={item.action_status === "completed" ? "secondary" : "default"}
                                  >
                                    {item.action_status}
                                  </Badge>
                                </div>
                                {item.assignee && (
                                  <p className="text-sm text-muted-foreground mb-2">
                                    Assigned to: {item.assignee}
                                  </p>
                                )}
                                <div className="flex justify-between items-center">
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(item.date).toLocaleDateString()}
                                  </span>
                                  <div className="flex gap-1">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => {
                                        setEditingItem(item.item_id);
                                        setEditForm({
                                          title: item.title,
                                          assignee: item.assignee || "",
                                          action_status: item.action_status,
                                        });
                                      }}
                                    >
                                      Edit
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => deleteActionItem(item.item_id)}
                                    >
                                      Delete
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
