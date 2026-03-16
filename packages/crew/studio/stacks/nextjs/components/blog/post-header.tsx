import Link from "next/link";
import { ArrowLeft, Calendar, Clock, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { BlogPost } from "@/lib/blog";

interface PostHeaderProps {
  post: BlogPost;
  backLabel: string;
  publishedLabel: string;
  byLabel: string;
  readTimeLabel: string;
}

export function PostHeader({
  post,
  backLabel,
  publishedLabel,
  byLabel,
  readTimeLabel,
}: PostHeaderProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6">
      <Link
        href="/blog"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        {backLabel}
      </Link>

      <div className="flex flex-wrap gap-1.5 mb-4" role="list" aria-label="Tags">
        {post.tags.map((tag) => (
          <Badge key={tag} variant="outline" role="listitem">
            {tag}
          </Badge>
        ))}
      </div>

      <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground tracking-tight mb-4">
        {post.title}
      </h1>

      <p className="text-lg text-muted-foreground mb-6">
        {post.description}
      </p>

      <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground pb-8 border-b border-border">
        <time dateTime={post.date} className="flex items-center gap-1.5">
          <Calendar className="w-4 h-4" aria-hidden="true" />
          {publishedLabel}{" "}
          {new Date(post.date).toLocaleDateString("fr-BE", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </time>
        <span className="flex items-center gap-1.5">
          <User className="w-4 h-4" aria-hidden="true" />
          {byLabel} {post.author}
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="w-4 h-4" aria-hidden="true" />
          {post.readTime} {readTimeLabel}
        </span>
      </div>
    </div>
  );
}
