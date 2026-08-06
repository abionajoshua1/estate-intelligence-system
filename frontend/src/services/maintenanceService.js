import api from "@/api/axios";

const maintenanceService = {
  getTeams: async () => {
    const res = await api.get("maintenance-teams/");
    return res.data;
  },

  getTeam: async (id) => {
    const res = await api.get(`maintenance-teams/${id}/`);
    return res.data;
  },

  createTeam: async (data) => {
    const res = await api.post("maintenance-team/create/", data);
    return res.data;
  },

  updateTeam: async (id, data) => {
    const res = await api.put(`maintenance-teams/${id}/update/`, data);
    return res.data;
  },

  deleteTeam: async (id) => {
    const res = await api.delete(`maintenance-teams/${id}/delete/`);
    return res.data;
  },
};

export default maintenanceService;