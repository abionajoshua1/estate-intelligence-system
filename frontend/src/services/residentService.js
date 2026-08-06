import api from "@/api/axios";

const residentService = {
  getResidents: async () => {
    const res = await api.get("residents/");
    return res.data;
  },

  createResident: async (data) => {
    const res = await api.post("residents/create/", data);
    return res.data;
  },

  updateResident: async (residentId, data) => {
    const res = await api.put(`residents/${residentId}/`, data);
    return res.data;
  },

  deleteResident: async (residentId) => {
    const res = await api.delete(`residents/${residentId}/delete/`);
    return res.data;
  },

  assignProperty: async (data) => {
    const res = await api.post("residents/assign-property/", data);
    return res.data;
  },
};

export default residentService;