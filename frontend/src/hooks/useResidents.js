import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import residentService from "@/services/residentService";

export const useResidents = () => {
  return useQuery({
    queryKey: ["residents"],
    queryFn: residentService.getResidents,
  });
};

export const useCreateResident = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: residentService.createResident,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["residents"],
      });
    },
  });
};

export const useUpdateResident = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ residentId, data }) =>
      residentService.updateResident(residentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["residents"],
      });
    },
  });
};

export const useDeleteResident = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: residentService.deleteResident,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["residents"],
      });
    },
  });
};

export const useAssignResidentProperty = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: residentService.assignProperty,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["residents"],
      });

      queryClient.invalidateQueries({
        queryKey: ["properties"],
      });
    },
  });
};