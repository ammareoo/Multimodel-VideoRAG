"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { ChatInterface } from "@/components/ChatInterface";
import { getVideoStatus, videoUrl } from "@/lib/api";

export default function ChatPage({ params }: { params: { videoId: string } }) {
  const [ready, setReady] = useState(false);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getVideoStatus(params.videoId)
      .then((job) => {
        if (job.status !== "completed") {
          setError("Video is still processing. Please wait.");
          return;
        }
        setTitle(job.url);
        setReady(true);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Video not found"));
  }, [params.videoId]);

  if (error) {
    return <p className="text-center text-red-400">{error}</p>;
  }

  if (!ready) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Video Chat</h1>
        <p className="truncate text-sm text-muted-foreground">{title}</p>
      </div>
      <ChatInterface videoId={params.videoId} videoUrl={videoUrl(params.videoId)} />
    </div>
  );
}
