import { ProcessingStatus } from "@/components/ProcessingStatus";

export default function StatusPage({ params }: { params: { jobId: string } }) {
  return <ProcessingStatus jobId={params.jobId} />;
}
