"use client";

import Script from "next/script";
import { Suspense, useEffect, useState } from "react";
import { GA_ID } from "@/lib/analytics";
import { getConsentStatus } from "@/components/cookie-banner";

function AnalyticsInner() {
  const [consented, setConsented] = useState(false);

  useEffect(() => {
    setConsented(getConsentStatus() === "accepted");
  }, []);

  if (!GA_ID || !consented) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive"
      />
      <Script id="ga4-init" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_ID}', { page_path: window.location.pathname });
        `}
      </Script>
    </>
  );
}

export function Analytics() {
  return (
    <Suspense fallback={null}>
      <AnalyticsInner />
    </Suspense>
  );
}
