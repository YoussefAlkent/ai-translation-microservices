import Link from "next/link";
import { ThemeToggle } from "./theme-toggle";

const navigationLinks = [
  { href: "/services/text-summarizer", label: "Text Summarizer" },
  { href: "/services/english2arabic", label: "English to Arabic" },
  { href: "/services/arabic2english", label: "Arabic to English" },
];

export function Navbar() {
  return (
    <nav className="border-b">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-bold text-xl">
            AI Tools
          </Link>
          <div className="hidden md:flex items-center gap-4">
            {navigationLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm font-medium hover:text-primary transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-sm font-medium hover:text-primary transition-colors"
          >
            Login
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </nav>
  );
}
