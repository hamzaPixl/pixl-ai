"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Send, CheckCircle, Loader2 } from "lucide-react";
import { useTranslate } from "@/hooks/useTranslate";
import { trackContactFormSubmit } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

const contactSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Please enter a valid email"),
  phone: z.string().optional(),
  message: z.string().min(10, "Message must be at least 10 characters"),
});

type ContactFormData = z.infer<typeof contactSchema>;

export function ContactForm() {
  const { t } = useTranslate();
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
  });

  async function onSubmit(data: ContactFormData) {
    setStatus("sending");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        setStatus("sent");
        reset();
        trackContactFormSubmit();
        setTimeout(() => setStatus("idle"), 4000);
      } else {
        setStatus("error");
        setTimeout(() => setStatus("idle"), 4000);
      }
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 4000);
    }
  }

  return (
    <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("contactForm.name")}
        </Label>
        <Input
          id="name"
          type="text"
          placeholder={t("contactForm.namePlaceholder")}
          className="mt-1.5"
          aria-required="true"
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? "name-error" : undefined}
          {...register("name")}
        />
        {errors.name && (
          <p id="name-error" role="alert" className="text-xs text-destructive mt-1">{errors.name.message}</p>
        )}
      </div>

      <div>
        <Label htmlFor="email" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("contactForm.email")}
        </Label>
        <Input
          id="email"
          type="email"
          placeholder={t("contactForm.emailPlaceholder")}
          className="mt-1.5"
          aria-required="true"
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? "email-error" : undefined}
          {...register("email")}
        />
        {errors.email && (
          <p id="email-error" role="alert" className="text-xs text-destructive mt-1">{errors.email.message}</p>
        )}
      </div>

      <div>
        <Label htmlFor="phone" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("contactForm.phone")}
        </Label>
        <Input
          id="phone"
          type="tel"
          placeholder={t("contactForm.phonePlaceholder")}
          className="mt-1.5"
          {...register("phone")}
        />
      </div>

      <div>
        <Label htmlFor="message" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("contactForm.message")}
        </Label>
        <Textarea
          id="message"
          rows={4}
          placeholder={t("contactForm.messagePlaceholder")}
          className="mt-1.5 resize-none"
          aria-required="true"
          aria-invalid={!!errors.message}
          aria-describedby={errors.message ? "message-error" : undefined}
          {...register("message")}
        />
        {errors.message && (
          <p id="message-error" role="alert" className="text-xs text-destructive mt-1">{errors.message.message}</p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={status === "sending"} aria-busy={status === "sending"}>
        {status === "sending" ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />
            {t("contactForm.submit")}
          </>
        ) : status === "sent" ? (
          <>
            <CheckCircle className="w-4 h-4 mr-2" aria-hidden="true" />
            {t("common.messageSent")}
          </>
        ) : (
          <>
            <Send className="w-4 h-4 mr-2" aria-hidden="true" />
            {t("contactForm.submit")}
          </>
        )}
      </Button>

      {status === "error" && (
        <p role="alert" className="text-xs text-destructive text-center">
          {t("common.errorOccurred")}
        </p>
      )}
    </form>
  );
}
