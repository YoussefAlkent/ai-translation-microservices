import { Button } from "@/components/ui/button";
import Link from "next/link";
import {Navbar} from "@/components/navbar";

export default function HomePage() {
  return (
    <>
      <Navbar />
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
      <div className="container px-4 md:px-6">
        <div className="flex flex-col items-center space-y-4 text-center">
          <h1 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl lg:text-6xl">
            AI Language Tools
          </h1>
          <p className="mx-auto max-w-[700px] text-gray-500 md:text-xl dark:text-gray-400">
            Translate between Arabic and English, or summarize text using advanced AI.
          </p>
          <div className="space-x-4">
            <Button asChild>
              <Link href="/services/text-summarizer">Get Started</Link>
            </Button>
          </div>
          </div>
        </div>
      </div>
    </>
  );
}