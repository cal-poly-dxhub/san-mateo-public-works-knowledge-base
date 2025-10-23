"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import SearchComponent from "@/components/SearchComponent";

export default function SearchPage() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Base Search</CardTitle>
          <p className="text-sm text-muted-foreground">
            Search documents and lessons learned across all projects
          </p>
        </CardHeader>
        <CardContent>
          <SearchComponent placeholder="Ask a question..." />
        </CardContent>
      </Card>
    </div>
  );
}
