import api from "@/api/axios";

const managerService = {
  getManagers: async () => {
    const res = await api.get("managers/");
    return res.data;
  },

  createManager: async (data) => {
    const res = await api.post("managers/create/", data);
    return res.data;
  },

  updateManager: async (id, data) => {
    const res = await api.put(`managers/${id}/`, data);
    return res.data;
  },

  deleteManager: async (id) => {
    const res = await api.delete(`managers/${id}/delete/`);
    return res.data;
  },
};

export default managerService;