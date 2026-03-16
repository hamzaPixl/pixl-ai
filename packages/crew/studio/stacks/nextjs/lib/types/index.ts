export interface PageSeoDTO {
  title: string;
  description: string;
  keywords: string[];
}

export interface ServiceItem {
  slug: string;
  icon: string;
  title: string;
  shortDescription: string;
  fullDescription: string;
  problem: string;
  methodology: string[];
  deliverables: string[];
  benefits: string[];
}

export interface TeamMember {
  name: string;
  role: string;
  expertise: string;
  phone: string;
  linkedin: string;
  bio: string;
}

export interface TestimonialItem {
  name: string;
  role: string;
  company: string;
  rating: number;
  quote: string;
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface ProcessStep {
  number: string;
  title: string;
  description: string;
}

export interface StatItem {
  value: string;
  suffix: string;
  label: string;
}

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  date: string;
  author: string;
  tags: string[];
  image?: string;
  readTime: number;
  content: string;
}
