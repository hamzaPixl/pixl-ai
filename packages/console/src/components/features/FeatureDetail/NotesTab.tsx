import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export interface NotesTabProps {
  notes: string[] | undefined;
  noteText: string;
  onNoteTextChange: (text: string) => void;
  onAddNote: () => void;
  isPending: boolean;
}

export function NotesTab({
  notes,
  noteText,
  onNoteTextChange,
  onAddNote,
  isPending,
}: NotesTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <input
          type="text"
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
          placeholder="Add a note..."
          value={noteText}
          onChange={(e) => onNoteTextChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && noteText.trim()) {
              onAddNote();
            }
          }}
        />
        <Button
          size="sm"
          disabled={!noteText.trim() || isPending}
          onClick={onAddNote}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>
      {notes && notes.length > 0 ? (
        <div className="space-y-2">
          {notes.map((note, i) => (
            <div
              key={i}
              className="text-sm border rounded-md px-3 py-2 bg-muted/30"
            >
              {note}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground py-4 text-center">
          No notes yet.
        </p>
      )}
    </div>
  );
}
