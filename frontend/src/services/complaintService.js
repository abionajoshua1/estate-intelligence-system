import api from "@/api/axios";

const complaintService = {
  getComplaints: async () => {
    const res = await api.get("complaints/");
    return res.data;
  },

  createComplaint: async (data) => {
    const res = await api.post("complaints/create/", data);
    return res.data;
  },

  updateComplaint: async (complaintId, data) => {
    const res = await api.put(`complaints/${complaintId}/`, data);
    return res.data;
  },

  deleteComplaint: async (complaintId) => {
    const res = await api.delete(`complaints/${complaintId}/delete/`);
    return res.data;
  },

  assignProperty: async (data) => {
    const res = await api.post("complaints/assign-property/", data);
    return res.data;
  },

  assignTeam: async (data) => {
    const res = await api.post("complaints/assign-team/", data);
    return res.data;
  },
};

export default complaintService;