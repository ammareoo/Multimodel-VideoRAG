import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UrlForm } from "@/components/UrlForm";

export default function SubmitPage() {
  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>Submit YouTube Video</CardTitle>
          <CardDescription>
            Videos are downloaded at 360p (max 480p) for efficient free-tier processing.
            Processing includes scene detection, transcription, OCR, and multimodal indexing.
          </CardDescription>
        </CardHeader>
        <UrlForm />
      </Card>
    </div>
  );
}
