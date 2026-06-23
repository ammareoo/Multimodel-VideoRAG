"use client";

import Image from "next/image";
import { Clock, FileText, ImageIcon, Mic } from "lucide-react";
import { EvidenceItem, frameUrl } from "@/lib/api";
import { cn, formatTimestamp } from "@/lib/utils";

interface Props {
  evidence: EvidenceItem[];
  videoId: string;
  selectedId?: string;
  onSelect?: (item: EvidenceItem) => void;
}

const modalityIcon: Record<string, typeof Mic> = {
  transcript: Mic,
  ocr: FileText,
  visual: ImageIcon,
};

const modalityColor: Record<string, string> = {
  transcript: "text-blue-400",
  ocr: "text-amber-400",
  visual: "text-purple-400",
};

export function EvidencePanel({ evidence, videoId, selectedId, onSelect }: Props) {
  if (!evidence.length) {
    return (
      <div className="glass rounded-xl p-6 text-center text-sm text-muted-foreground">
        Evidence will appear here after you ask a question.
      </div>
    );
  }

  return (
    <div className="glass max-h-[calc(100vh-12rem)] overflow-y-auto rounded-xl p-4">
      <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
        <Clock className="h-4 w-4" />
        Evidence ({evidence.length})
      </h3>
      <div className="space-y-3">
        {evidence.map((item) => {
          const Icon = modalityIcon[item.modality] || FileText;
          const filename = item.frame_path?.split("/").pop();

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect?.(item)}
              className={cn(
                "w-full rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/50",
                selectedId === item.id && "border-primary bg-primary/5"
              )}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className={cn("flex items-center gap-1.5 text-xs font-medium capitalize", modalityColor[item.modality])}>
                  <Icon className="h-3.5 w-3.5" />
                  {item.modality}
                </span>
                <span className="font-mono text-xs text-primary">
                  {formatTimestamp(item.timestamp_start)}
                </span>
              </div>
              <p className="line-clamp-3 text-sm text-foreground/90">{item.text}</p>
              {filename && item.modality !== "transcript" && (
                <div className="relative mt-2 h-20 w-full overflow-hidden rounded-md">
                  <Image
                    src={frameUrl(videoId, filename)}
                    alt={`Frame at ${formatTimestamp(item.timestamp_start)}`}
                    fill
                    className="object-cover"
                    unoptimized
                  />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
