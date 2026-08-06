import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

const COLLAPSE_STORAGE_KEY = "eis:sidebar-collapsed";

/**
 * AppLayout
 *
 * Top-level application shell for every authenticated route. Wraps the
 * page content (rendered via <Outlet />) with a collapsible Sidebar and a
 * sticky Topbar. Sidebar collapse state persists across sessions;
 * mobile drawer state resets on every route change.
 *
 * Usage (in routes/index.jsx or similar):
 *
 *   <Route element={<AppLayout />}>
 *     <Route path="/" element={<Dashboard />} />
 *     <Route path="/residents" element={<Residents />} />
 *     ...
 *   </Route>
 */
export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === "true";
  });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(COLLAPSE_STORAGE_KEY, String(collapsed));
  }, [collapsed]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((prev) => !prev)}
        mobileOpen={mobileNavOpen}
        onMobileOpenChange={setMobileNavOpen}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMobileMenuClick={() => setMobileNavOpen(true)} />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}