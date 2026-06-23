import Link from "next/link";
import { ArrowRight, Eye, FileSearch, Mic, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UrlForm } from "@/components/UrlForm";

const features = [
  {
    icon: Mic,
    title: "Speech Understanding",
    desc: "Timestamped transcription with semantic chunking and overlap.",
  },
  {
    icon: Eye,
    title: "Visual Scenes",
    desc: "Scene keyframe detection — no wasteful per-frame processing.",
  },
  {
    icon: FileSearch,
    title: "OCR & Slides",
    desc: "Reads whiteboards, slides, code, and on-screen text.",
  },
  {
    icon: Sparkles,
    title: "Grounded Answers",
    desc: "Hybrid retrieval + reranking. Evidence-only responses.",
  },
];

export default function Home() {
  return (
    <div className="space-y-16">
      <section className="text-center">
        <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">
          Multimodal <span className="text-primary">VideoRAG</span>
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-muted-foreground">
          Paste a YouTube URL. Ask questions about speech, slides, visuals, and timestamps.
          Built with free open-source models — no paid APIs required.
        </p>
        <div className="mx-auto max-w-xl">
          <Card>
            <UrlForm />
          </Card>
        </div>
        <Link href="/submit" className="mt-4 inline-block">
          <Button variant="ghost" size="sm">
            Advanced submission <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </Link>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <Card key={f.title}>
            <CardHeader>
              <f.icon className="mb-2 h-8 w-8 text-primary" />
              <CardTitle className="text-base">{f.title}</CardTitle>
              <CardDescription>{f.desc}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </section>
    </div>
  );
}
