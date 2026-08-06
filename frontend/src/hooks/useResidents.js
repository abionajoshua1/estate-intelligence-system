import { useQuery } from "@tanstack/react-query";
import residentService from "@/services/residentService";

export const useResidents = () => {
  return useQuery({
    queryKey: ["residents"],
    queryFn: residentService.getResidents,
  });
};