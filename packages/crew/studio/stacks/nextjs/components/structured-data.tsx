import { baseUrl, identity } from "@/lib/config";

export function StructuredData() {
  const organization = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: identity.name,
    url: identity.url,
    logo: `${baseUrl}/logo.svg`,
    contactPoint: {
      "@type": "ContactPoint",
      email: identity.contactEmail,
      telephone: identity.phone,
    },
  };

  const website = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: identity.name,
    url: baseUrl,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(website) }}
      />
    </>
  );
}
