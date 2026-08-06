import { useQuery } from "@tanstack/react-query";
import maintenanceService from "@/services/maintenanceService";

export function useMaintenanceTeams() {
  return useQuery({
    queryKey: ["maintenance-teams"],
    queryFn: maintenanceService.getTeams,
  });
}