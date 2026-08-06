import { useQuery } from "@tanstack/react-query";
import dashboardService from "@/services/dashboardService";

/**
 * One hook per dashboard/* endpoint, each independently loadable/erroring
 * so a single failed widget doesn't take down the whole page.
 */

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: dashboardService.overview,
  });
}

export function useComplaintsByCategory() {
  return useQuery({
    queryKey: ["dashboard", "complaints-by-category"],
    queryFn: dashboardService.complaintsByCategory,
  });
}

export function usePropertiesByStatus() {
  return useQuery({
    queryKey: ["dashboard", "properties-by-status"],
    queryFn: dashboardService.propertiesByStatus,
  });
}

export function useTopResidents() {
  return useQuery({
    queryKey: ["dashboard", "top-residents"],
    queryFn: dashboardService.topResidents,
  });
}

export function useTopProperties() {
  return useQuery({
    queryKey: ["dashboard", "top-properties"],
    queryFn: dashboardService.topProperties,
  });
}

export function useRecentComplaints() {
  return useQuery({
    queryKey: ["dashboard", "recent-complaints"],
    queryFn: dashboardService.recentComplaints,
  });
}