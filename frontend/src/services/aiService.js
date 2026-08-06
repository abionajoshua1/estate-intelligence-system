import api from "@/api/axios";

const aiService = {
  askAI: async (data) => {
    const res = await api.post("ai/", data);
    return res.data;
  },

  askAIV2: async (data) => {
    const res = await api.post("ai/v2/", data);
    return res.data;
  },

  askAIV3: async (data) => {
    const res = await api.post("ai/v3/", data);
    return res.data;
  },

  testAI: async () => {
    const res = await api.get("ai/test/");
    return res.data;
  },
};

export default aiService;