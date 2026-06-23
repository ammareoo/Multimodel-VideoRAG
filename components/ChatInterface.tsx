"use client";

import { useRef, useState } from "react";
import { Loader2, MessageSquare, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { askQuestion, AskResponse, EvidenceItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EvidencePanel } from "./EvidencePanel";

interface Message {
  role: "user" | "assistant";
  content: string;
  evidence?: EvidenceItem[];
  confidence?: string;
  insufficient?: boolean;
}

interface Props {
  videoId: string;
  videoUrl?: string;
}

const SUGGESTIONS = [
  "What was written on the whiteboard or slides?",
  "What graph or diagram appeared?",
  "Summarize the main topics discussed.",
  "What happened after the speaker mentioned a key concept?",
];

export function ChatInterface({ videoId, videoUrl }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState<EvidenceItem[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | undefined>();
  const videoRef = useRef<HTMLVideoElement>(null);

  async function handleAsk(question: string) {
    if (!question.trim() || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const response: AskResponse = await askQuestion(videoId, question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          evidence: response.evidence,
          confidence: response.confidence,
          insufficient: response.insufficient_evidence,
        },
      ]);
      setActiveEvidence(response.evidence);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Failed to get answer",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function seekTo(timestamp: number) {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.play();
    }
  }

  function handleEvidenceSelect(item: EvidenceItem) {
    setSelectedEvidence(item);
    seekTo(item.timestamp_start);
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 space-y-4">
        {videoUrl && (
          <Card className="overflow-hidden p-0">
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              className="w-full aspect-video bg-black"
            />
          </Card>
        )}

        <Card className="flex h-[500px] flex-col">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Ask About This Video
            </CardTitle>
            <CardDescription>
              Grounded answers from transcript, OCR, and visual scene evidence.
            </CardDescription>
          </CardHeader>

          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="space-y-3 py-8 text-center">
                <p className="text-muted-foreground">Try one of these questions:</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleAsk(s)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs hover:bg-muted"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "max-w-[90%] rounded-xl px-4 py-3 text-sm",
                  msg.role === "user"
                    ? "ml-auto bg-primary text-primary-foreground"
                    : "bg-muted"
                )}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.confidence && (
                  <p className="mt-2 text-xs opacity-70">
                    Confidence: {msg.confidence}
                    {msg.insufficient && " — limited evidence"}
                  </p>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching multimodal evidence...
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(input);
            }}
            className="flex gap-2 border-t border-border p-4"
          >
            <Input
              placeholder="Ask about slides, visuals, speech, timestamps..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </Card>
      </div>

      <EvidencePanel
        evidence={activeEvidence}
        videoId={videoId}
        selectedId={selectedEvidence?.id}
        onSelect={handleEvidenceSelect}
      />
    </div>
  );
}
