"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import { cn } from "@/lib/utils";
import { formatTimeAgo } from "@/lib/format-utils";
import { User } from "lucide-react";

interface Comment {
  id: string;
  text: string;
  created_at: string;
  author?: string;
}

interface CommentThreadProps {
  entityId: string;
  entityType: "session" | "run";
  comments?: Comment[];
  onSubmit?: (text: string) => void;
}

function draftKey(entityId: string): string {
  return `comment-draft:${entityId}`;
}

export function CommentThread({
  entityId,
  entityType,
  comments = [],
  onSubmit,
}: CommentThreadProps) {
  const [draft, setDraft] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem(draftKey(entityId));
    if (saved) setDraft(saved);
  }, [entityId]);

  // Persist draft to localStorage
  useEffect(() => {
    if (draft) {
      localStorage.setItem(draftKey(entityId), draft);
    } else {
      localStorage.removeItem(draftKey(entityId));
    }
  }, [draft, entityId]);

  function handleSubmit() {
    const text = draft.trim();
    if (!text) return;
    onSubmit?.(text);
    setDraft("");
    localStorage.removeItem(draftKey(entityId));
  }

  return (
    <div className="space-y-3">
      {comments.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No comments on this {entityType} yet.
        </p>
      )}

      {comments.map((comment) => (
        <Card key={comment.id} className="shadow-none">
          <CardContent className="p-3 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="h-5 w-5 rounded-full bg-muted flex items-center justify-center">
                <User className="h-3 w-3" />
              </div>
              <span className="font-medium text-foreground">
                {comment.author ?? "System"}
              </span>
              <span>&middot;</span>
              <time>{formatTimeAgo(comment.created_at)}</time>
            </div>
            <div className="text-sm prose-sm max-w-none">
              <Markdown>{comment.text}</Markdown>
            </div>
          </CardContent>
        </Card>
      ))}

      <div className="space-y-2">
        <textarea
          className={cn(
            "w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
            "placeholder:text-muted-foreground focus-visible:outline-none",
            "focus-visible:ring-1 focus-visible:ring-ring resize-y min-h-[72px]"
          )}
          placeholder="Add a comment (Markdown supported)..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              handleSubmit();
            }
          }}
        />
        <div className="flex justify-end">
          <Button
            size="sm"
            disabled={!draft.trim()}
            onClick={handleSubmit}
          >
            Comment
          </Button>
        </div>
      </div>
    </div>
  );
}
