interface StreamingTextDisplayProps {
  text: string;
  isStreaming: boolean;
}

export function StreamingTextDisplay({ text, isStreaming }: StreamingTextDisplayProps) {
  return (
    <div className="space-y-2">
      {isStreaming && (
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          <span className="text-xs text-primary">
            Listening...
          </span>
        </div>
      )}
      <div className="min-h-[40px] rounded-md border border-input bg-background p-3 text-xs leading-relaxed text-foreground">
        {text || (
          <span className="text-muted-foreground">
            Hold Ctrl+Space to start dictation...
          </span>
        )}
      </div>
    </div>
  );
}
