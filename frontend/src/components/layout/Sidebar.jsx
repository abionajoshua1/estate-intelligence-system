import { NavLink, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Users,
  Building2,
  AlertTriangle,
  MessageSquare,
  ChevronsLeft,
  ChevronsRight,
  Building,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { useAuth } from "@/context/AuthContext";

/**
 * Navigation based on user role
 */
const getNavItems = (role) => {
  const items = [
    {
      label: "Dashboard",
      to: "/",
      icon: LayoutDashboard,
      end: true,
    },
    {
      label: "AI Chat",
      to: "/chat",
      icon: MessageSquare,
    },
  ];

  // Manager/Admin can manage residents & properties
  if (role === "manager" || role === "admin") {
    items.push(
      {
        label: "Residents",
        to: "/residents",
        icon: Users,
      },
      {
        label: "Properties",
        to: "/properties",
        icon: Building2,
      }
    );
  }

  // Everyone can see complaints
  items.push({
    label: "Complaints",
    to: "/complaints",
    icon: AlertTriangle,
  });

  return items;
};

const SIDEBAR_EXPANDED_WIDTH = 272;
const SIDEBAR_COLLAPSED_WIDTH = 80;

/**
 * Brand
 */
function BrandMark({ collapsed }) {
  return (
    <div
      className={cn(
        "flex h-16 items-center gap-2.5 px-4",
        collapsed && "justify-center px-0"
      )}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Building className="h-5 w-5" strokeWidth={2} />
      </div>

      {!collapsed && (
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-semibold">
            Estate Intelligence
          </p>

          <p className="truncate text-xs text-muted-foreground">
            Property Operations
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Shared Navigation List
 */
function NavList({
  collapsed,
  onNavigate,
  items,
}) {
  const location = useLocation();

  return (
    <TooltipProvider delayDuration={200}>
      <nav className="flex flex-col gap-1 px-3">
        {items.map(({ label, to, icon: Icon, end }) => {
          const isActive = end
            ? location.pathname === to
            : location.pathname.startsWith(to);

          const link = (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onNavigate}
              className={cn(
                "group relative flex items-center rounded-lg text-sm font-medium transition-colors",
                collapsed
                  ? "justify-center px-0 py-2.5"
                  : "gap-3 px-3 py-2.5",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {isActive && (
                <motion.span
                  layoutId="sidebar-active-indicator"
                  className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary"
                  transition={{
                    type: "spring",
                    stiffness: 500,
                    damping: 40,
                  }}
                />
              )}

              <Icon
                className="h-[18px] w-[18px] shrink-0"
                strokeWidth={1.75}
              />

              {!collapsed && (
                <span className="truncate">{label}</span>
              )}
            </NavLink>
          );

          if (!collapsed) return link;

          return (
            <Tooltip key={to}>
              <TooltipTrigger asChild>
                {link}
              </TooltipTrigger>

              <TooltipContent
                side="right"
                sideOffset={12}
              >
                {label}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </nav>
    </TooltipProvider>
  );
}

/**
 * Sidebar
 */
export default function Sidebar({
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onMobileOpenChange,
}) {
  const { user } = useAuth();

  const navItems = getNavItems(user?.role);

  return (
    <>
      {/* Desktop Sidebar */}

      <motion.aside
        initial={false}
        animate={{
          width: collapsed
            ? SIDEBAR_COLLAPSED_WIDTH
            : SIDEBAR_EXPANDED_WIDTH,
        }}
        transition={{
          type: "tween",
          duration: 0.2,
          ease: "easeInOut",
        }}
        className="relative hidden shrink-0 border-r bg-card lg:flex lg:flex-col"
      >
        <BrandMark collapsed={collapsed} />

        <Separator />

        <div className="flex-1 overflow-y-auto py-4">
          <NavList
            collapsed={collapsed}
            items={navItems}
          />
        </div>

        <Separator />

        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleCollapsed}
            className={cn(
              "w-full text-muted-foreground",
              collapsed
                ? "justify-center px-0"
                : "justify-start gap-2"
            )}
          >
            {collapsed ? (
              <ChevronsRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronsLeft className="h-4 w-4" />
                <span>Collapse</span>
              </>
            )}
          </Button>
        </div>
      </motion.aside>

      {/* Mobile Sidebar */}

      <Sheet
        open={mobileOpen}
        onOpenChange={onMobileOpenChange}
      >
        <SheetContent
          side="left"
          className="w-72 p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>
              Navigation Menu
            </SheetTitle>
          </SheetHeader>

          <BrandMark collapsed={false} />

          <Separator />

          <div className="py-4">
            <NavList
              collapsed={false}
              items={navItems}
              onNavigate={() =>
                onMobileOpenChange(false)
              }
            />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

export {
  SIDEBAR_EXPANDED_WIDTH,
  SIDEBAR_COLLAPSED_WIDTH,
};