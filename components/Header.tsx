import Link from "next/link";
import { Video } from "lucide-react";

export function Header() {
  return (
    <header className="border-b border-border/50">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Video className="h-6 w-6 text-primary" />
          <span>VideoRAG</span>
        </Link>
        <nav className="flex gap-4 text-sm">
          <Link href="/submit" className="text-muted-foreground hover:text-foreground">
            Submit
          </Link>
        </nav>
      </div>
    </header>
  );
}
