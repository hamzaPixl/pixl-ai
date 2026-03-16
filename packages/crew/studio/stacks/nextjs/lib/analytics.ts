declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
    dataLayer: unknown[];
  }
}

export const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";

export function pageview(url: string) {
  if (typeof window === "undefined" || !GA_ID) return;
  window.gtag("config", GA_ID, { page_path: url });
}

export function event(action: string, params?: Record<string, unknown>) {
  if (typeof window === "undefined" || !GA_ID) return;
  window.gtag("event", action, params);
}

export function trackCTA(label: string) {
  event("cta_click", { event_label: label });
}

export function trackAppointment(platform: string, practitioner: string) {
  event("appointment_click", { platform, practitioner });
}

export function trackPhoneCall() {
  event("phone_click", { event_label: "header_phone" });
}

export function trackContactFormSubmit() {
  event("contact_form_submit", { event_category: "engagement" });
}

export function trackSectionView(sectionName: string) {
  event("section_view", { event_label: sectionName });
}
