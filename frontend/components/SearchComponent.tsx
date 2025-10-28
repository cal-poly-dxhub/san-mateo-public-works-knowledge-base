"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useApiKey } from "@/lib/api-context";
import { apiRequest } from "@/lib/api";
import { Search, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Source {
  content: string;
  source: string;
  project: string;
  relevance_score: number;
  chunk_index: string;
  total_chunks: string;
}

interface SearchResult {
  answer: string;
  sources: Source[];
}

interface SearchComponentProps {
  projectName?: string; // Optional - if provided, searches within project
  placeholder?: string;
}

export default function SearchComponent({ projectName, placeholder = "Ask a question..." }: SearchComponentProps) {
  const { apiKey } = useApiKey();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const [searchType, setSearchType] = useState<"both" | "lessons" | "documents">("both");
  const [ragEnabled, setRagEnabled] = useState(true);
  const [docLimit, setDocLimit] = useState("10");
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");

  useEffect(() => {
    if (apiKey) {
      loadAvailableModels();
    }
  }, [apiKey]);

  const loadAvailableModels = async () => {
    try {
      const data = await apiRequest("/models");
      const models = Array.isArray(data) ? data : (data.available_search_models || []);
      setAvailableModels(models);
      if (models.length > 0) {
        setSelectedModel(models[0].id);
      }
    } catch (error) {
      console.error("Error loading models:", error);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const body: any = { query, limit: parseInt(docLimit), model_id: selectedModel };

      // For documents, filter by project. For lessons, search globally
      if (searchType === "lessons") {
        body.is_lesson = true;
      } else if (searchType === "documents") {
        body.is_lesson = false;
        if (projectName) body.project_name = projectName;
      } else if (searchType === "both") {
        if (projectName) body.project_name = projectName;
      }

      // Choose endpoint based on RAG mode
      const endpoint = ragEnabled ? "/search-rag" : "/search";
      
      const data = await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });
      
      if (ragEnabled) {
        // RAG response: { answer, sources }
        setResult({ answer: data.answer, sources: data.sources || [] });
        setExpandedSources(new Set()); // Collapse all in RAG mode
      } else {
        // Non-RAG response: { results } - already in correct format
        const results = data.results || [];
        setResult({ answer: "", sources: results });
        // Auto-expand all sources in non-RAG mode
        setExpandedSources(new Set(results.map((_: any, i: number) => i)));
      }
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (index: number) => {
    const newExpanded = new Set(expandedSources);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSources(newExpanded);
  };

  return (
    <div className="space-y-4">
      {/* Search Type Filter */}
      <div className="flex gap-2">
        <Button
          variant={searchType === "both" ? "default" : "outline"}
          size="sm"
          onClick={() => setSearchType("both")}
        >
          Both
        </Button>
        <Button
          variant={searchType === "lessons" ? "default" : "outline"}
          size="sm"
          onClick={() => setSearchType("lessons")}
        >
          Lessons Only
        </Button>
        <Button
          variant={searchType === "documents" ? "default" : "outline"}
          size="sm"
          onClick={() => setSearchType("documents")}
        >
          Documents Only
        </Button>
      </div>

      {/* Search Bar */}
      <div className="flex gap-2">
        <Input
          placeholder={placeholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1"
        />
        {ragEnabled && (
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select AI Model" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((model) => (
                <SelectItem key={model.id} value={model.id}>
                  {model.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select value={docLimit} onValueChange={setDocLimit}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[5, 10, 15, 20].map((num) => (
              <SelectItem key={num} value={num.toString()}>
                {num} docs
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex items-center gap-2 px-3 border rounded-md">
          <Switch
            id="rag-mode"
            checked={ragEnabled}
            onCheckedChange={setRagEnabled}
          />
          <Label htmlFor="rag-mode" className="cursor-pointer whitespace-nowrap">
            AI Summary
          </Label>
        </div>
        <Button onClick={handleSearch} disabled={loading}>
          <Search className="h-4 w-4 mr-2" />
          {loading ? "Searching..." : "Search"}
        </Button>
      </div>

      {result && (
        <div className="space-y-6 mt-6">
          {/* Answer - only show if RAG enabled */}
          {ragEnabled && result.answer && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Answer</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-4 [&_h2]:mb-2 [&_strong]:font-semibold [&_ul]:my-2 [&_li]:my-1">
                  <ReactMarkdown>{result.answer}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Sources */}
          {result.sources && result.sources.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">
                {ragEnabled ? "Sources" : `Top ${result.sources.length} Results`}
              </h3>
              {result.sources.map((source, index) => (
                <Card key={index} className="border">
                  <CardHeader
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => toggleSource(index)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline">[{index + 1}]</Badge>
                        <div>
                          <a 
                            href={`${process.env.NEXT_PUBLIC_API_URL || 'https://42redkfdhl.execute-api.us-west-2.amazonaws.com/prod'}/projects/${encodeURIComponent(source.project)}/assets/${encodeURIComponent(source.source)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-primary hover:underline flex items-center gap-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {source.source}
                            <ExternalLink className="h-3 w-3" />
                          </a>
                          <p className="text-sm text-muted-foreground">
                            Project: {source.project} • Chunk {source.chunk_index}/{source.total_chunks}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {source.relevance_score}% match
                        </Badge>
                        {expandedSources.has(index) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  {expandedSources.has(index) && (
                    <CardContent>
                      <p className="text-sm whitespace-pre-wrap bg-muted p-4 rounded">
                        {source.content}
                      </p>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
