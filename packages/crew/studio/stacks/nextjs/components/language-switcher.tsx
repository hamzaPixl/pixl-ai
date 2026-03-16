"use client";

import { useLanguage, type Locale } from "@/lib/language-context";
import { Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const locales: { code: Locale; label: string; full: string }[] = [
  { code: "fr", label: "FR", full: "Français" },
  { code: "nl", label: "NL", full: "Nederlands" },
  { code: "en", label: "EN", full: "English" },
];

export function LanguageSwitcher({ compact }: { compact?: boolean }) {
  const { currentLanguage, setLanguage } = useLanguage();

  const current = locales.find((l) => l.code === currentLanguage);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size={compact ? "sm" : "default"}
          className={compact ? "h-7 px-2 text-[10px] gap-1" : "h-8 px-2.5 text-xs gap-1.5"}
        >
          <Globe className={compact ? "w-3 h-3" : "w-3.5 h-3.5"} />
          {current?.label}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map(({ code, label, full }) => (
          <DropdownMenuItem
            key={code}
            onClick={() => setLanguage(code)}
            className={currentLanguage === code ? "bg-accent" : ""}
          >
            <span className="font-medium mr-2">{label}</span>
            <span className="text-muted-foreground">{full}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
