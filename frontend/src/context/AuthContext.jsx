import { createContext, useContext, useEffect, useState } from "react";
import API from "@/api/axios";
import authService from "@/services/authService";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const register = async (data) => {
  return await authService.register(data);
};

  const login = async (username, password) => {
    const tokenRes = await API.post("/token/", {
      username,
      password,
    });

    localStorage.setItem("access", tokenRes.data.access);
    localStorage.setItem("refresh", tokenRes.data.refresh);

    API.defaults.headers.common[
      "Authorization"
    ] = `Bearer ${tokenRes.data.access}`;

    const userRes = await API.get("/me/");

    setUser(userRes.data);

    return userRes.data;
  };

  const logout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");

    delete API.defaults.headers.common["Authorization"];

    setUser(null);
  };

  useEffect(() => {
    const token = localStorage.getItem("access");

    if (!token) {
      setLoading(false);
      return;
    }

    API.defaults.headers.common["Authorization"] = `Bearer ${token}`;

    API.get("/me/")
      .then((res) => {
        setUser(res.data);
      })
      .catch(() => {
        logout();
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        register,
        logout,
        loading,

        isResident: user?.role === "resident",
        isManager: user?.role === "manager",
        isAdmin: user?.role === "admin",
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}