import { useState } from "react";
import {
  AlertCircle,
  UserRound,
  AtSign,
  Mail,
  ShieldCheck,
  LogOut,
  Lock,
  Settings,
  Home,
  Building2,
  Hash,
  CheckCircle2,
  Loader2,
  Eye,
  EyeOff,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import api from "@/api/axios";

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const ROLE_STYLES = {
  admin: {
    label: "Administrator",
    accent: "text-violet-600 bg-violet-500/10 dark:text-violet-400",
    ring: "ring-violet-500/30",
    description:
      "Full administrative access to manage estates, properties, and residents.",
  },
  manager: {
    label: "Manager",
    accent: "text-blue-600 bg-blue-500/10 dark:text-blue-400",
    ring: "ring-blue-500/30",
    description:
      "Manages day-to-day operations across assigned properties.",
  },
  resident: {
    label: "Resident",
    accent: "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400",
    ring: "ring-emerald-500/30",
    description:
      "Can view property details and manage complaints and notifications.",
  },
};

const DEFAULT_ROLE_STYLE = {
  label: "Member",
  accent: "text-amber-600 bg-amber-500/10 dark:text-amber-400",
  ring: "ring-amber-500/30",
  description:
    "Your account role determines what you can access in this workspace.",
};

const RESIDENT_FIELDS = [
  { key: "property", label: "Property", icon: Building2 },
  { key: "property_name", label: "Property", icon: Building2 },
  { key: "unit", label: "Unit", icon: Home },
  { key: "unit_number", label: "Unit", icon: Home },
  { key: "estate", label: "Estate", icon: Building2 },
  { key: "estate_name", label: "Estate", icon: Building2 },
  { key: "resident_id", label: "Resident ID", icon: Hash },
];

const NAV_ITEMS = [
  { key: "profile", label: "Profile", icon: UserRound },
  { key: "account", label: "Account", icon: Settings },
  { key: "security", label: "Security", icon: Lock },
];

function getInitials(value) {
  if (typeof value !== "string" || !value.trim()) return "?";

  const parts = value.trim().split(/\s+/).filter(Boolean);

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatContactLine(username, email) {
  if (username && email) return `${username} · ${email}`;
  if (username) return username;
  if (email) return email;
  return "No account details on file";
}

function IconChip({ icon: Icon, className = "" }) {
  return (
    <span
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted ${className}`}
    >
      <Icon className="h-4 w-4" />
    </span>
  );
}

function InfoRow({ icon, label, value }) {
  const hasValue =
    value !== undefined && value !== null && value !== "";

  const displayValue = hasValue ? String(value) : "—";

  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="flex min-w-0 shrink-0 items-center gap-3 text-sm text-muted-foreground">
        <IconChip icon={icon} />
        {label}
      </div>

      <span
        className="min-w-0 truncate text-right text-sm font-medium"
        title={hasValue ? displayValue : undefined}
      >
        {displayValue}
      </span>
    </div>
  );
}

function ProfileLoading() {
  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-6 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col items-center gap-4 sm:flex-row">
            <div className="h-14 w-14 animate-pulse rounded-full bg-muted sm:h-16 sm:w-16" />

            <div className="space-y-2">
              <div className="h-4 w-36 animate-pulse rounded bg-muted" />
              <div className="h-3 w-48 animate-pulse rounded bg-muted" />
            </div>
          </div>

          <div className="h-9 w-full animate-pulse rounded-md bg-muted sm:w-28" />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <div className="flex gap-1 lg:flex-col">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-9 w-24 shrink-0 animate-pulse rounded-md bg-muted lg:w-full"
            />
          ))}
        </div>

        <Card>
          <CardContent className="space-y-4 py-6">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-5 w-full animate-pulse rounded bg-muted"
              />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ProfileUnavailable() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-10 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-5 w-5 text-destructive" />
      </span>

      <div>
        <p className="text-sm font-medium text-destructive">
          We couldn't load your profile
        </p>

        <p className="mt-1 text-sm text-muted-foreground">
          Please try signing in again.
        </p>
      </div>
    </div>
  );
}

function EditProfileForm({ user, onUserUpdated }) {
  const [firstName, setFirstName] = useState(user.first_name || "");
  const [lastName, setLastName] = useState(user.last_name || "");

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    setIsSaving(true);
    setError("");
    setSuccess("");

    try {
      const response = await api.patch("me/", {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });

      onUserUpdated(response.data);

      setSuccess("Profile updated successfully.");
    } catch (error) {
      console.error(
        "PROFILE UPDATE ERROR:",
        error?.response?.data || error
      );

      const data = error?.response?.data;

      if (data && typeof data === "object") {
        const messages = Object.entries(data)
          .flatMap(([field, value]) => {
            const values = Array.isArray(value) ? value : [value];

            return values.map(
              (message) =>
                `${field.replace("_", " ")}: ${message}`
            );
          })
          .join(" ");

        setError(messages || "Unable to update your profile.");
      } else {
        setError("Unable to update your profile. Please try again.");
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="first-name" className="text-sm font-medium">
            First name
          </label>

          <Input
            id="first-name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            placeholder="Enter your first name"
            disabled={isSaving}
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="last-name" className="text-sm font-medium">
            Last name
          </label>

          <Input
            id="last-name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            placeholder="Enter your last name"
            disabled={isSaving}
          />
        </div>
      </div>

      <div className="rounded-lg border bg-muted/30 p-4">
        <div className="flex items-start gap-3">
          <Mail className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />

          <div>
            <p className="text-sm font-medium">Email address</p>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {user.email || "No email address"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Email changes are not available from this page.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <Button type="submit" disabled={isSaving}>
        {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {isSaving ? "Saving..." : "Save changes"}
      </Button>
    </form>
  );
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder,
  visible,
  setVisible,
  disabled,
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>

      <div className="relative">
        <Input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete={
            id === "current-password"
              ? "current-password"
              : "new-password"
          }
          className="pr-10"
        />

        <button
          type="button"
          onClick={() => setVisible((prev) => !prev)}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
          aria-label={visible ? `Hide ${label}` : `Show ${label}`}
        >
          {visible ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}


function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const getErrorMessage = (data) => {
    if (!data) {
      return "Unable to change your password. Please try again.";
    }

    if (typeof data === "string") {
      return data;
    }

    if (data.detail) {
      return Array.isArray(data.detail)
        ? data.detail.join(" ")
        : String(data.detail);
    }

    return Object.entries(data)
      .flatMap(([field, value]) => {
        const values = Array.isArray(value) ? value : [value];

        return values.map(
          (message) =>
            `${field.replaceAll("_", " ")}: ${message}`
        );
      })
      .join(" ");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setIsSaving(true);
    setError("");
    setSuccess("");

    try {
      await api.post("change-password/", {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      setSuccess("Password changed successfully.");
    } catch (error) {
      console.error(
        "CHANGE PASSWORD ERROR:",
        error?.response?.data || error
      );

      setError(getErrorMessage(error?.response?.data));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <PasswordField
        id="current-password"
        label="Current password"
        value={currentPassword}
        onChange={setCurrentPassword}
        placeholder="Enter your current password"
        visible={showCurrent}
        setVisible={setShowCurrent}
        disabled={isSaving}
      />

      <PasswordField
        id="new-password"
        label="New password"
        value={newPassword}
        onChange={setNewPassword}
        placeholder="Enter your new password"
        visible={showNew}
        setVisible={setShowNew}
        disabled={isSaving}
      />

      <PasswordField
        id="confirm-password"
        label="Confirm new password"
        value={confirmPassword}
        onChange={setConfirmPassword}
        placeholder="Confirm your new password"
        visible={showConfirm}
        setVisible={setShowConfirm}
        disabled={isSaving}
      />

      <div className="rounded-lg border bg-muted/30 p-4">
        <p className="text-xs text-muted-foreground">
          Your new password must satisfy the password validation rules
          configured by the system.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <Button
        type="submit"
        disabled={
          isSaving ||
          !currentPassword ||
          !newPassword ||
          !confirmPassword
        }
      >
        {isSaving && (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        )}
        {isSaving ? "Changing password..." : "Change password"}
      </Button>
    </form>
  );
}

export default function Profile() {
  const { user, loading, logout, setUser } = useAuth();
  const [activeSection, setActiveSection] = useState("profile");

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Profile
          </h1>

          <p className="text-sm text-muted-foreground">
            Your account details and role within the Estate Intelligence
            System.
          </p>
        </div>

        <ProfileLoading />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Profile
          </h1>

          <p className="text-sm text-muted-foreground">
            Your account details and role within the Estate Intelligence
            System.
          </p>
        </div>

        <Card>
          <CardContent className="py-6">
            <ProfileUnavailable />
          </CardContent>
        </Card>
      </div>
    );
  }

  const fullName = [user.first_name, user.last_name]
    .filter(Boolean)
    .join(" ")
    .trim();

  const displayName = fullName || user.username || "Unnamed User";

  const roleStyle =
    ROLE_STYLES[user.role] || DEFAULT_ROLE_STYLE;

  const residentFields = RESIDENT_FIELDS.filter(
    (field) =>
      user[field.key] !== undefined &&
      user[field.key] !== null &&
      user[field.key] !== ""
  );

  const seenLabels = new Set();

  const dedupedResidentFields = residentFields.filter((field) => {
    if (seenLabels.has(field.label)) return false;

    seenLabels.add(field.label);
    return true;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Profile
        </h1>

        <p className="text-sm text-muted-foreground">
          Manage your account details, security, and access.
        </p>
      </div>

      {/* Identity header */}
      <Card>
        <CardContent className="flex flex-col gap-6 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
            <Avatar
              className={`h-14 w-14 shrink-0 text-lg ring-2 ring-offset-2 ring-offset-background sm:h-16 sm:w-16 ${roleStyle.ring}`}
            >
              <AvatarFallback className={roleStyle.accent}>
                {getInitials(fullName || user.username)}
              </AvatarFallback>
            </Avatar>

            <div className="min-w-0 space-y-1.5">
              <div className="flex flex-col items-center gap-2 sm:flex-row">
                <h2
                  className="max-w-full truncate text-lg font-semibold"
                  title={displayName}
                >
                  {displayName}
                </h2>

                <Badge
                  variant="secondary"
                  className={`shrink-0 gap-1 whitespace-nowrap ${roleStyle.accent}`}
                >
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {roleStyle.label}
                </Badge>
              </div>

              <p
                className="max-w-full truncate text-sm text-muted-foreground"
                title={formatContactLine(
                  user.username,
                  user.email
                )}
              >
                {formatContactLine(user.username, user.email)}
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full shrink-0 gap-1.5 transition-colors hover:border-destructive/40 hover:text-destructive sm:w-auto"
            onClick={logout}
          >
            <LogOut className="h-3.5 w-3.5" />
            Log out
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        {/* Section navigation */}
        <nav
          aria-label="Profile sections"
          className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible"
        >
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.key;

            return (
              <button
                key={item.key}
                type="button"
                aria-current={isActive ? "page" : undefined}
                onClick={() => setActiveSection(item.key)}
                className={`flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 lg:shrink ${
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="space-y-6">
          {/* Profile */}
          {activeSection === "profile" && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <UserRound className="h-4 w-4 text-muted-foreground" />
                    Your access
                  </CardTitle>

                  <CardDescription>
                    A quick overview of your role and what it means.
                  </CardDescription>
                </CardHeader>

                <CardContent>
                  <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-4">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md ${roleStyle.accent}`}
                    >
                      <ShieldCheck className="h-4 w-4" />
                    </span>

                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {roleStyle.label}
                      </p>

                      <p className="text-sm text-muted-foreground">
                        {roleStyle.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {user.role === "resident" && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      Resident information
                    </CardTitle>

                    <CardDescription>
                      Property and unit details tied to your resident
                      account.
                    </CardDescription>
                  </CardHeader>

                  <CardContent
                    className={
                      dedupedResidentFields.length > 0
                        ? "divide-y"
                        : undefined
                    }
                  >
                    {dedupedResidentFields.length > 0 ? (
                      dedupedResidentFields.map((field) => (
                        <InfoRow
                          key={field.key}
                          icon={field.icon}
                          label={field.label}
                          value={user[field.key]}
                        />
                      ))
                    ) : (
                      <div className="flex flex-col items-center gap-2 py-8 text-center">
                        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                          <Building2 className="h-5 w-5 text-muted-foreground" />
                        </span>

                        <p className="text-sm font-medium">
                          No resident details yet
                        </p>

                        <p className="max-w-xs text-sm text-muted-foreground">
                          Your property and estate information will
                          appear here once it's linked to your account.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* Account */}
          {activeSection === "account" && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-4 w-4 text-muted-foreground" />
                  Edit profile
                </CardTitle>

                <CardDescription>
                  Update the name associated with your account.
                </CardDescription>
              </CardHeader>

              <CardContent>
                <EditProfileForm
                  user={user}
                  onUserUpdated={setUser}
                />
              </CardContent>
            </Card>
          )}

          {/* Security */}
          {activeSection === "security" && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-muted-foreground" />
                  Change password
                </CardTitle>

                <CardDescription>
                  Update the password used to sign in to your account.
                </CardDescription>
              </CardHeader>

              <CardContent>
                <ChangePasswordForm />
              </CardContent>
            </Card>
          )}

          {/* Account information */}
          {activeSection === "account" && (
            <Card>
              <CardHeader>
                <CardTitle>Account information</CardTitle>

                <CardDescription>
                  Details associated with your authenticated account.
                </CardDescription>
              </CardHeader>

              <CardContent className="divide-y">
                <InfoRow
                  icon={UserRound}
                  label="Username"
                  value={user.username}
                />

                <InfoRow
                  icon={Mail}
                  label="Email"
                  value={user.email}
                />

                <InfoRow
                  icon={ShieldCheck}
                  label="Role"
                  value={roleStyle.label}
                />

                <InfoRow
                  icon={AtSign}
                  label="User ID"
                  value={user.id}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
