import api from "@/api/axios";

const dashboardService = {
  overview: async () => {
    const res = await api.get("dashboard/overview/");
    return res.data;
  },

  complaintsByCategory: async () => {
    const res = await api.get("dashboard/complaints-by-category/");
    return res.data;
  },

  propertiesByStatus: async () => {
    const res = await api.get("dashboard/properties-by-status/");
    return res.data;
  },

  topResidents: async () => {
    const res = await api.get("dashboard/top-residents/");
    return res.data;
  },

  topProperties: async () => {
    const res = await api.get("dashboard/top-properties/");
    return res.data;
  },

  recentComplaints: async () => {
    const res = await api.get("dashboard/recent-complaints/");
    return res.data;
  },
};

export default dashboardService;