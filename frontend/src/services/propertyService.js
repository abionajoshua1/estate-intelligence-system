import api from "@/api/axios";

const propertyService = {
  getProperties: async () => {
    const res = await api.get("properties/");
    return res.data;
  },

  createProperty: async (data) => {
    const res = await api.post("properties/create/", data);
    return res.data;
  },

  updateProperty: async (propertyId, data) => {
    const res = await api.put(`properties/${propertyId}/`, data);
    return res.data;
  },

  deleteProperty: async (propertyId) => {
    const res = await api.delete(`properties/${propertyId}/delete/`);
    return res.data;
  },
};

export default propertyService;