import api from "@/api/axios";

const authService = {
  register: async (data) => {
    const res = await api.post("register/", data);
    return res.data;
  },

  currentUser: async () => {
    const res = await api.get("me/");
    return res.data;
  },
};

export default authService;