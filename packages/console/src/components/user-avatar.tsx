import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getUserInitials } from "@/lib/user-utils";
import { cn } from "@/lib/utils";

const sizeClasses = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-xs",
  lg: "h-16 w-16 text-lg",
} as const;

interface UserAvatarProps {
  firstName?: string | null;
  lastName?: string | null;
  size?: keyof typeof sizeClasses;
  muted?: boolean;
}

export function UserAvatar({ firstName, lastName, size = "md", muted = false }: UserAvatarProps) {
  const initials = getUserInitials(firstName, lastName);

  return (
    <Avatar className={cn(sizeClasses[size])}>
      <AvatarFallback
        className={cn(
          "font-medium",
          muted ? "bg-muted text-muted-foreground" : "bg-primary text-primary-foreground"
        )}
      >
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}
