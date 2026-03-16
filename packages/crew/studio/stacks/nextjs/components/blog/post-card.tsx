import Link from "next/link";
import { ArrowRight, Calendar, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BlogPost } from "@/lib/blog";

interface PostCardProps {
  post: BlogPost;
  readMoreLabel: string;
  readTimeLabel: string;
}

export function PostCard({ post, readMoreLabel, readTimeLabel }: PostCardProps) {
  return (
    <Card className="h-full flex flex-col group">
      <CardContent className="p-6 flex flex-col flex-1">
        <div className="flex flex-wrap gap-1.5 mb-3" role="list" aria-label="Tags">
          {post.tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs" role="listitem">
              {tag}
            </Badge>
          ))}
        </div>

        <h2 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors mb-2">
          <Link href={`/blog/${post.slug}`} className="hover:underline">
            {post.title}
          </Link>
        </h2>

        <p className="text-sm text-muted-foreground leading-relaxed mb-4 flex-1">
          {post.description}
        </p>

        <div className="flex items-center justify-between pt-4 border-t border-border">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <time
              dateTime={post.date}
              className="flex items-center gap-1"
            >
              <Calendar className="w-3 h-3" aria-hidden="true" />
              {new Date(post.date).toLocaleDateString("fr-BE", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </time>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" aria-hidden="true" />
              {post.readTime} {readTimeLabel}
            </span>
          </div>
          <Link
            href={`/blog/${post.slug}`}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            aria-label={`${readMoreLabel}: ${post.title}`}
          >
            {readMoreLabel}
            <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
