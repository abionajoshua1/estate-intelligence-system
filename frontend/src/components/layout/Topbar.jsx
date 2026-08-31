import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/api/axios";

import { useNavigate } from "react-router-dom";
import {
  Menu,
  Search,
  Bell,
  User,
  Settings,
  LogOut,
  Loader2,
  Building2,
  AlertTriangle,
  Map,
  UserCog,
  Wrench,
  SearchX,
} from "lucide-react";

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

// Maps a search result's entity type to display icon, label, and route.
const SEARCH_TYPE_CONFIG = {
  Resident: { icon: User, label: "Resident", route: "/residents" },
  Property: { icon: Building2, label: "Property", route: "/properties" },
  Complaint: { icon: AlertTriangle, label: "Complaint", route: "/complaints" },
  Estate: { icon: Map, label: "Estate", route: "/dashboard" },
  Manager: { icon: UserCog, label: "Manager", route: "/dashboard" },
  MaintenanceTeam: { icon: Wrench, label: "Maintenance Team", route: "/dashboard" },
};

const DEFAULT_TYPE_CONFIG = { icon: Search, label: "Result", route: "/dashboard" };

function getTypeConfig(type) {
  return SEARCH_TYPE_CONFIG[type] || DEFAULT_TYPE_CONFIG;
}

// TODO: replace with the authenticated user from your auth/session store.

// Formats an ISO timestamp as a short relative time (e.g. "5m ago", "2h ago").
function formatNotificationTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";

  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.round(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

function NotificationsMenu() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function fetchNotifications() {
      setIsLoading(true);
      setHasError(false);
      try {
        const response = await api.get("dashboard/notifications/");
        if (!isMounted) return;
        const data = response.data || {};
        console.log("NOTIFICATIONS API RESPONSE:", data);
        setNotifications(Array.isArray(data.notifications) ? data.notifications : []);
        setUnreadCount(typeof data.unread_count === "number" ? data.unread_count : 0);
      } catch (error) {
        console.error("NOTIFICATIONS FETCH ERROR:", error?.response?.data || error);
        if (isMounted) setHasError(true);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchNotifications();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleNotificationClick = async (notification) => {
    if (notification.is_read) return;

    try {
      await api.patch(`dashboard/notifications/${notification.id}/read/`);
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notification.id ? { ...n, is_read: true } : n
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("NOTIFICATION MARK READ ERROR:", error?.response?.data || error);
    }
  };

  // Reuses the existing per-notification PATCH endpoint (no bulk endpoint
  // exists on the backend), firing one request per unread notification.
  const handleMarkAllRead = async (event) => {
    event.preventDefault();

    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length === 0) return;

    const results = await Promise.allSettled(
      unreadIds.map((id) => api.patch(`dashboard/notifications/${id}/read/`))
    );

    const succeededIds = new Set();

    results.forEach((result, index) => {
      if (result.status === "fulfilled") {
        succeededIds.add(unreadIds[index]);
      } else {
        console.error("NOTIFICATION MARK READ ERROR:", result.reason?.response?.data || result.reason);
      }
    });

    if (succeededIds.size === 0) return;

    setNotifications((prev) =>
      prev.map((n) => (succeededIds.has(n.id) ? { ...n, is_read: true } : n))
    );
    setUnreadCount((prev) => Math.max(0, prev - succeededIds.size));
  };

  console.log("NOTIFICATIONS STATE:", notifications);
  console.log("NOTIFICATIONS LENGTH:", notifications.length);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          {unreadCount > 0 && (
            <Badge className="absolute -right-1 -top-1 h-4 min-w-4 rounded-full px-1 text-[10px] leading-4">
              {unreadCount}
            </Badge>
          )}
          <span className="sr-only">Notifications</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-[420px] max-h-[600px] overflow-y-auto"
      >
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notifications</span>
          <span className="text-xs font-normal text-muted-foreground">
            {unreadCount} new
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {unreadCount > 0 && (
          <DropdownMenuItem
            onClick={handleMarkAllRead}
            className="justify-center text-xs font-medium text-primary"
          >
            Mark all as read
          </DropdownMenuItem>
        )}
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 px-3 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading notifications...
          </div>
        ) : hasError ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            Couldn't load notifications. Please try again later.
          </div>
        ) : notifications.length === 0 ? (
          <div className="px-3 py-4 text-center text-sm text-muted-foreground">
            No notifications yet.
          </div>
        ) : (
          notifications.map((n) => (
            <DropdownMenuItem
              key={n.id}
              onClick={() => handleNotificationClick(n)}
              className={`flex flex-col items-start gap-0.5 py-2.5 ${
                n.is_read ? "opacity-60" : ""
              }`}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="text-sm font-medium">{n.title}</span>
                <span className="shrink-0 text-[11px] text-muted-foreground">
                  {formatNotificationTime(n.created_at)}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {n.description}
              </span>
            </DropdownMenuItem>
          ))
        )}
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
 * GlobalSearch
 *
 * Application-wide search box. Debounces requests to GET /api/search/?q=,
 * shows a dropdown of results grouped by entity type, and routes to the
 * relevant list page (or /dashboard as a fallback) on selection.
 */
function GlobalSearch() {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const debounceRef = useRef(null);
  const requestIdRef = useRef(0);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const runSearch = useCallback(async (q) => {
    const currentRequestId = ++requestIdRef.current;
    setIsLoading(true);
    try {
      const response = await api.get(`search/?q=${encodeURIComponent(q)}`);
      if (currentRequestId !== requestIdRef.current) return; // stale response

      const data = response.data;
      const list = Array.isArray(data) ? data : data?.results || [];
      setResults(list);
      setHasSearched(true);
      setActiveIndex(-1);
    } catch (error) {
      if (currentRequestId !== requestIdRef.current) return;
      console.error("SEARCH ERROR:", error?.response?.data || error);
      setResults([]);
      setHasSearched(true);
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = query.trim();

    if (!trimmed) {
      requestIdRef.current += 1; // invalidate any in-flight request
      setResults([]);
      setIsLoading(false);
      setHasSearched(false);
      setActiveIndex(-1);
      return;
    }

    setIsOpen(true);
    debounceRef.current = setTimeout(() => {
      runSearch(trimmed);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, runSearch]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleFocus = () => {
    if (query.trim()) setIsOpen(true);
  };

  const handleSelect = (result) => {
    const { route } = getTypeConfig(result.type);
    navigate(route);
    setQuery("");
    setResults([]);
    setHasSearched(false);
    setIsOpen(false);
    setActiveIndex(-1);
    inputRef.current?.blur();
  };

  const handleKeyDown = (event) => {
    if (!isOpen || results.length === 0) {
      if (event.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((prev) => (prev - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0 && activeIndex < results.length) {
        handleSelect(results[activeIndex]);
      }
    } else if (event.key === "Escape") {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  const showDropdown = isOpen && (isLoading || hasSearched);

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

      <Input
        ref={inputRef}
        type="search"
        role="combobox"
        aria-expanded={showDropdown}
        aria-autocomplete="list"
        placeholder="Search residents, properties, complaints..."
        className="pl-9 pr-9"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
      />

      {isLoading && (
        <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
      )}

      {showDropdown && (
        <div className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 max-h-96 overflow-y-auto rounded-md border bg-popover text-popover-foreground shadow-md">
          {isLoading && results.length === 0 ? (
            <div className="flex items-center gap-2 px-4 py-4 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching...
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center gap-1.5 px-4 py-6 text-center">
              <SearchX className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">No results found</span>
              <span className="text-xs text-muted-foreground">
                Try a different search term.
              </span>
            </div>
          ) : (
            <ul role="listbox" className="py-1.5">
              {results.map((result, index) => {
                const { icon: Icon, label } = getTypeConfig(result.type);
                const isActive = index === activeIndex;
                return (
                  <li key={`${result.type}-${result.id ?? index}`}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={isActive}
                      onClick={() => handleSelect(result)}
                      onMouseEnter={() => setActiveIndex(index)}
                      className={`flex w-full items-start gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
                        isActive ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"
                      }`}
                    >
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="flex items-center justify-between gap-2">
                          <span className="truncate font-medium">
                            {result.title || result.name || "Untitled"}
                          </span>
                          <Badge
                            variant="secondary"
                            className="shrink-0 text-[10px] font-normal"
                          >
                            {label}
                          </Badge>
                        </span>
                        {(
                          result.subtitle ||
                          result.related_estate ||
                          result.related_property ||
                          result.related_resident ||
                          result.description ||
                          result.context
                        ) && (
                          <span className="truncate text-xs text-muted-foreground">
                            {[
                              result.subtitle,
                              result.related_estate,
                              result.related_property,
                              result.related_resident,
                              result.description,
                              result.context,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        )}
                        {result.id !== undefined && result.id !== null && (
                          <span className="text-[11px] text-muted-foreground/70">
                            ID: {result.id}
                          </span>
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
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

      <GlobalSearch />

      <div className="ml-auto flex items-center gap-1.5">
        <NotificationsMenu />
        <Separator orientation="vertical" className="mx-1 h-6" />
        <UserMenu />
      </div>
    </header>
  );
}