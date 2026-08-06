import { useQuery } from "@tanstack/react-query";
import complaintService from "@/services/complaintService";

export function useComplaints() {
  return useQuery({
    queryKey: ["complaints"],
    queryFn: complaintService.getComplaints,
  });
}