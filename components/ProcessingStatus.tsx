"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getJobStatus, JobStatusResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

const STAGES = [
  { key: "downloading", label: "Download" },
  { key: "compressing", label: "Compress" },
  { key: "scene_detection", label: "Segments" },
  { key: "transcribing", label: "Transcribe" },
  { key: "extracting_frames", label: "Frames" },
  { key: "ocr", label: "OCR" },
  { key: "embedding", label: "Embed" },
  { key: "indexing", label: "Index" },
  { key: "completed", label: "Ready" },
];

interface Props {
  jobId: string;
}

export function ProcessingStatus({ jobId }: Props) {
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const data = await getJobStatus(jobId);
        if (!active) return;
        setError("");
        setJob(data);
        if (data.status === "completed") {
          router.push(`/chat/${data.video_id}`);
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to fetch status");
      }
    }

    poll();
    const interval = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [jobId, router]);

  if (error) {
    return (
      <Card className="border-red-500/30">
        <p className="text-red-400">{error}</p>
      </Card>
    );
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const isFailed = job.status === "failed";
  const failedStage =
    isFailed && typeof job.metadata?.failed_stage === "string"
      ? job.metadata.failed_stage
      : undefined;
  const currentIdx = failedStage
    ? STAGES.findIndex((s) => s.key === failedStage)
    : STAGES.findIndex((s) => s.key === job.status);
  const isQueued = job.status === "pending";

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isQueued ? "Queued for Processing" : "Processing Video"}</CardTitle>
        <CardDescription className="truncate">{job.url}</CardDescription>
      </CardHeader>

      {isQueued && (
        <p className="mb-4 text-sm text-muted-foreground">
          Waiting for worker to pick up the job. Ensure the worker process is running.
        </p>
      )}

      <div className="mb-6">
        <div className="mb-2 flex justify-between text-sm">
          <span>{job.message}</span>
          <span className="text-muted-foreground">{job.progress}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        {STAGES.map((stage, idx) => {
          const done =
            job.status === "completed"
              ? currentIdx > idx || stage.key === "completed"
              : isFailed
                ? idx < currentIdx
                : currentIdx > idx;
          const active = !isFailed && stage.key === job.status;
          const failedHere = isFailed && idx === currentIdx;

          return (
            <div
              key={stage.key}
              className={cn(
                "flex flex-col items-center rounded-lg p-2 text-center text-xs",
                done && "text-green-400",
                active && "bg-primary/10 text-primary",
                failedHere && "text-red-400"
              )}
            >
              {done ? (
                <CheckCircle2 className="mb-1 h-4 w-4" />
              ) : active ? (
                <Loader2 className="mb-1 h-4 w-4 animate-spin" />
              ) : failedHere ? (
                <XCircle className="mb-1 h-4 w-4" />
              ) : (
                <div className="mb-1 h-4 w-4 rounded-full border border-border" />
              )}
              {stage.label}
            </div>
          );
        })}
      </div>

      {job.status === "failed" && (
        <div className="mt-6 space-y-3">
          <p className="text-sm text-red-400">{job.error || "Processing failed"}</p>
          <Button variant="outline" onClick={() => router.push("/submit")}>
            Try Another Video
          </Button>
        </div>
      )}
    </Card>
  );
}
