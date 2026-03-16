"use client";

import Link from "next/link";
import { SharedLayout } from "@/components/shared-layout";
import { ArrowLeft } from "lucide-react";
import { useTranslate } from "@/hooks/useTranslate";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  const { t } = useTranslate();

  return (
    <SharedLayout>
      <div className="min-h-[60vh] flex items-center justify-center px-4 hero-gradient">
        <div className="text-center max-w-md relative z-10">
          <p className="text-7xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent mb-4">
            404
          </p>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            {t("notFound.title")}
          </h1>
          <p className="text-muted-foreground mb-8">
            {t("notFound.description")}
          </p>
          <Button asChild>
            <Link href="/">
              <ArrowLeft className="w-4 h-4 mr-2" aria-hidden="true" />
              {t("notFound.cta")}
            </Link>
          </Button>
        </div>
      </div>
    </SharedLayout>
  );
}
