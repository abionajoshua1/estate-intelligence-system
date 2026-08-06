import { useQuery } from "@tanstack/react-query";
import managerService from "@/services/managerService";

export function useManagers() {
  return useQuery({
    queryKey: ["managers"],
    queryFn: managerService.getManagers,
  });
}