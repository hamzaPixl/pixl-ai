"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </div>
        <h1 className="font-serif text-2xl sm:text-3xl font-bold text-foreground mb-3">
          Une erreur est survenue
        </h1>
        <p className="text-muted-foreground mb-8 leading-relaxed">
          Nous sommes d&eacute;sol&eacute;s, quelque chose s&apos;est mal pass&eacute;. Veuillez
          r&eacute;essayer ou retourner &agrave; la page d&apos;accueil.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button onClick={reset} variant="default">
            <RotateCcw className="w-4 h-4 mr-2" />
            R&eacute;essayer
          </Button>
          <Button asChild variant="outline">
            <Link href="/">
              <Home className="w-4 h-4 mr-2" />
              Page d&apos;accueil
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
