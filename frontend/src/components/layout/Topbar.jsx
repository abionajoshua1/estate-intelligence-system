import { useNavigate } from "react-router-dom";
import { Menu, Search, Bell, User, Settings, LogOut } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// TODO: replace with real data via React Query, e.g.
// const { data: notifications = [] } = useQuery({ queryKey: ["notifications"], queryFn: fetchNotifications });
const PLACEHOLDER_NOTIFICATIONS = [
  {
    id: 1,
    title: "New complaint filed",
    description: "Block C, Unit 14 reported a plumbing issue.",
    time: "5m ago",
  },
  {
    id: 2,
    title: "Resident onboarded",
    description: "Amara Kone was added to Sunrise Towers.",
    time: "1h ago",
  },
  {
    id: 3,
    title: "AI insight ready",
    description: "Monthly occupancy report has been generated.",
    time: "3h ago",
  },
];

// TODO: replace with the authenticated user from your auth/session store.

function NotificationsMenu() {
  const count = PLACEHOLDER_NOTIFICATIONS.length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          {count > 0 && (
            <Badge className="absolute -right-1 -top-1 h-4 min-w-4 rounded-full px-1 text-[10px] leading-4">
              {count}
            </Badge>
          )}
          <span className="sr-only">Notifications</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notifications</span>
          <span className="text-xs font-normal text-muted-foreground">
            {count} new
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {PLACEHOLDER_NOTIFICATIONS.map((n) => (
          <DropdownMenuItem
            key={n.id}
            className="flex flex-col items-start gap-0.5 py-2.5"
          >
            <div className="flex w-full items-center justify-between gap-2">
              <span className="text-sm font-medium">{n.title}</span>
              <span className="shrink-0 text-[11px] text-muted-foreground">
                {n.time}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              {n.description}
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem className="justify-center text-sm font-medium text-primary">
          View all notifications
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function UserMenu() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();

  const CURRENT_USER = {
  name:
    `${user?.first_name || ""} ${user?.last_name || ""}`.trim() ||
    user?.username ||
    "Resident",

  email: user?.email || "",

  avatarUrl: "",

  initials:
    user?.first_name?.[0]?.toUpperCase() ||
    user?.username?.[0]?.toUpperCase() ||
    "R",
};

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex items-center gap-2 px-2 sm:pl-2 sm:pr-3"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={CURRENT_USER.avatarUrl} alt={CURRENT_USER.name} />
            <AvatarFallback className="text-xs">
              {CURRENT_USER.initials}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-sm font-medium sm:inline">
            {CURRENT_USER.name}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="end"
        sideOffset={8} 
        className="w-56 z-[9999]"
        >
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium">{CURRENT_USER.name}</p>
          <p className="truncate text-xs text-muted-foreground">
            {CURRENT_USER.email}
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate("/profile")}>
          <User className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate("/settings")}>
          <Settings className="mr-2 h-4 w-4" />
          Account settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleLogout}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * Topbar
 *
 * Sticky application header. Shows a mobile hamburger trigger (opens the
 * Sidebar's Sheet drawer via `onMobileMenuClick`), a global search field,
 * a notifications dropdown, and the user avatar menu.
 */
export default function Topbar({ onMobileMenuClick }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/75 sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMobileMenuClick}
      >
        <Menu className="h-5 w-5" />
        <span className="sr-only">Open navigation</span>
      </Button>

      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search residents, properties, complaints..."
          className="pl-9"
        />
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <NotificationsMenu />
        <Separator orientation="vertical" className="mx-1 h-6" />
        <UserMenu />
      </div>
    </header>
  );
}