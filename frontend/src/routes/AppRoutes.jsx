import { Routes, Route } from "react-router-dom";

import AppLayout from "@/components/layout/AppLayout";
import ProtectedRoute from "@/components/ProtectedRoute";

import Dashboard from "@/pages/Dashboard";
import Residents from "@/pages/Residents";
import Properties from "@/pages/Properties";
import Complaints from "@/pages/Complaints";
import Profile from "@/pages/Profile";
import Chat from "@/pages/Chat";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Settings from "@/pages/Settings";

export default function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      {/* Protected Layout */}
      <Route element={<AppLayout />}>

        {/* Dashboard */}
        <Route
          index
          element={
            <ProtectedRoute roles={["resident", "manager", "admin"]}>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute roles={["resident", "manager", "admin"]}>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Complaints */}
        <Route
          path="/complaints"
          element={
            <ProtectedRoute roles={["resident", "manager", "admin"]}>
              <Complaints />
            </ProtectedRoute>
          }
        />

        {/* AI Chat */}
        <Route
          path="/chat"
          element={
            <ProtectedRoute roles={["resident", "manager", "admin"]}>
              <Chat />
            </ProtectedRoute>
          }
        />

        {/* Profile */}
        <Route
          path="/profile"
          element={
            <ProtectedRoute roles={["resident", "manager", "admin"]}>
              <Profile />
            </ProtectedRoute>
          }
        />

        {/* Residents */}
        <Route
          path="/residents"
          element={
            <ProtectedRoute roles={["manager", "admin"]}>
              <Residents />
            </ProtectedRoute>
          }
        />

        {/* Properties */}
        <Route
          path="/properties"
          element={
            <ProtectedRoute roles={["manager", "admin"]}>
              <Properties />
            </ProtectedRoute>
          }
        />

        {/* Settings */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute roles={["admin"]}>
              <Settings />
            </ProtectedRoute>
          }
        />

      </Route>
    </Routes>
  );
}