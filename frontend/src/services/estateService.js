import api from "@/api/axios";

const estateService = {
  getEstates: async () => {
    const res = await api.get("estates/");
    return res.data;
  },

  createEstate: async (data) => {
    const res = await api.post("estates/create/", data);
    return res.data;
  },
};

export default estateService;