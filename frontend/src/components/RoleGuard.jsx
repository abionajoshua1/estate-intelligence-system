import { useAuth } from "../context/AuthContext";

export default function RoleGuard({
    roles,
    children
}) {
    const { user } = useAuth();

    if (!user) return null;

    if (!roles.includes(user.role)) {
        return null;
    }

    return children;
}