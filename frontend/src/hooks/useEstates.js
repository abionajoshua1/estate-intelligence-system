import { useQuery } from "@tanstack/react-query";
import estateService from "@/services/estateService";

export function useEstates() {
  return useQuery({
    queryKey: ["estates"],
    queryFn: getEstates,
  });
}