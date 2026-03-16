"use client";

import { usePathname } from "next/navigation";
import { baseUrl } from "@/lib/config";

const pathLabels: Record<string, string> = {
  about: "About",
  services: "Services",
  blog: "Blog",
  contact: "Contact",
  faq: "FAQ",
  legal: "Legal Notice",
  privacy: "Privacy Policy",
};

export function BreadcrumbSchema() {
  const pathname = usePathname();
  if (pathname === "/") return null;

  const segments = pathname.split("/").filter(Boolean);
  const items = [
    { "@type": "ListItem", position: 1, name: "Home", item: baseUrl },
  ];

  let currentPath = "";
  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    items.push({
      "@type": "ListItem",
      position: index + 2,
      name: pathLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " "),
      item: `${baseUrl}${currentPath}`,
    });
  });

  const schema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
