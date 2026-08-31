import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import complaintService from "@/services/complaintService";

export function useComplaints() {
  return useQuery({
    queryKey: ["complaints"],
    queryFn: complaintService.getComplaints,
  });
}

export function useCreateComplaint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: complaintService.createComplaint,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["complaints"],
      });
    },
  });
}

export function useUpdateComplaint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ complaintId, data }) =>
      complaintService.updateComplaint(complaintId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["complaints"],
      });
    },
  });
}

export function useDeleteComplaint() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: complaintService.deleteComplaint,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["complaints"],
      });
    },
  });
}

export function useAssignComplaintProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: complaintService.assignProperty,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["complaints"],
      });
    },
  });
}

export function useAssignComplaintTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: complaintService.assignTeam,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["complaints"],
      });
    },
  });
}