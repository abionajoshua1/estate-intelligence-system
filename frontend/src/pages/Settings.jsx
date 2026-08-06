import { useState } from "react";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  User,
  Palette,
  Bell,
  Sparkles,
  ShieldCheck,
  Info,
  KeyRound,
  LogOut,
  Monitor,
} from "lucide-react";

// TODO: replace with real app version source (e.g. package.json / build env var)
const APP_VERSION = "1.0.0";

function SettingsRow({ label, description, children }) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="max-w-md">
        <p className="text-sm font-medium">{label}</p>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function SectionCard({ icon, title, description, children }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start gap-3 space-y-0">
        <span className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
          {icon}
        </span>
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </CardHeader>
      <CardContent className="divide-y">{children}</CardContent>
    </Card>
  );
}

export default function Settings() {
  // Local-only UI state. Nothing here is persisted yet — see TODOs below.
  const [profile, setProfile] = useState({ name: "", email: "" });
  const [theme, setTheme] = useState("system");
  const [notifications, setNotifications] = useState({
    email: true,
    complaints: true,
    ai: false,
  });
  const [aiPreferences, setAiPreferences] = useState({
    responseLength: "balanced",
    suggestedPrompts: true,
  });

  const handleProfileChange = (field) => (e) =>
    setProfile((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSaveProfile = () => {
    // TODO: wire up to profile update endpoint once backend exists
  };

  const handleChangePassword = () => {
    // TODO: open change-password flow once backend/auth endpoint exists
  };

  const handleLogout = () => {
    // TODO: wire up to auth logout endpoint once backend exists
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account, preferences, and workspace settings.
        </p>
      </div>

      {/* Account */}
      <SectionCard
        icon={<User className="h-4 w-4" />}
        title="Account"
        description="Your personal information and login details."
      >
        <div className="flex flex-col gap-4 py-4 first:pt-0">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Profile name</label>
              <Input
                value={profile.name}
                onChange={handleProfileChange("name")}
                placeholder="Your name"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Email</label>
              <Input
                type="email"
                value={profile.email}
                onChange={handleProfileChange("email")}
                placeholder="you@example.com"
              />
            </div>
          </div>
          <div>
            <Button size="sm" onClick={handleSaveProfile}>
              Save profile
            </Button>
          </div>
        </div>

        <SettingsRow
          label="Password"
          description="Change the password used to sign in."
        >
          <Button variant="outline" size="sm" onClick={handleChangePassword} className="gap-2">
            <KeyRound className="h-4 w-4" />
            Change password
          </Button>
        </SettingsRow>
      </SectionCard>

      {/* Appearance */}
      <SectionCard
        icon={<Palette className="h-4 w-4" />}
        title="Appearance"
        description="Control how the app looks on your device."
      >
        <SettingsRow
          label="Theme"
          description="Choose light, dark, or match your system setting."
        >
          <Select value={theme} onValueChange={setTheme}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Theme" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
        </SettingsRow>
      </SectionCard>

      {/* Notifications */}
      <SectionCard
        icon={<Bell className="h-4 w-4" />}
        title="Notifications"
        description="Choose what you want to be notified about."
      >
        <SettingsRow
          label="Email notifications"
          description="Receive updates and summaries by email."
        >
          <Switch
            checked={notifications.email}
            onCheckedChange={(checked) =>
              setNotifications((prev) => ({ ...prev, email: checked }))
            }
          />
        </SettingsRow>

        <SettingsRow
          label="Complaint notifications"
          description="Get notified about new or updated complaints."
        >
          <Switch
            checked={notifications.complaints}
            onCheckedChange={(checked) =>
              setNotifications((prev) => ({ ...prev, complaints: checked }))
            }
          />
        </SettingsRow>

        <SettingsRow
          label="AI notifications"
          description="Get notified about AI-generated insights and responses."
        >
          <Switch
            checked={notifications.ai}
            onCheckedChange={(checked) =>
              setNotifications((prev) => ({ ...prev, ai: checked }))
            }
          />
        </SettingsRow>
      </SectionCard>

      {/* AI Preferences */}
      <SectionCard
        icon={<Sparkles className="h-4 w-4" />}
        title="AI preferences"
        description="Tune how the assistant responds to you."
      >
        <SettingsRow
          label="Response length"
          description="Choose how detailed AI responses should be."
        >
          <Select
            value={aiPreferences.responseLength}
            onValueChange={(value) =>
              setAiPreferences((prev) => ({ ...prev, responseLength: value }))
            }
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Response length" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="concise">Concise</SelectItem>
              <SelectItem value="balanced">Balanced</SelectItem>
              <SelectItem value="detailed">Detailed</SelectItem>
            </SelectContent>
          </Select>
        </SettingsRow>

        <SettingsRow
          label="Suggested prompts"
          description="Show suggested prompts on the chat welcome screen."
        >
          <Switch
            checked={aiPreferences.suggestedPrompts}
            onCheckedChange={(checked) =>
              setAiPreferences((prev) => ({ ...prev, suggestedPrompts: checked }))
            }
          />
        </SettingsRow>
      </SectionCard>

      {/* Security */}
      <SectionCard
        icon={<ShieldCheck className="h-4 w-4" />}
        title="Security"
        description="Manage where you're signed in."
      >
        <SettingsRow
          label="Active session"
          description="This device — session details will appear here once available."
        >
          {/* TODO: replace with real session data (device, location, last active) */}
          <span className="text-sm text-muted-foreground">
            <Monitor className="mr-1.5 inline h-4 w-4 align-text-bottom" />
            Current device
          </span>
        </SettingsRow>

        <SettingsRow
          label="Log out"
          description="Sign out of your account on this device."
        >
          <Button variant="destructive" size="sm" onClick={handleLogout} className="gap-2">
            <LogOut className="h-4 w-4" />
            Log out
          </Button>
        </SettingsRow>
      </SectionCard>

      {/* System */}
      <SectionCard
        icon={<Info className="h-4 w-4" />}
        title="System"
        description="App and backend information."
      >
        <SettingsRow label="App version">
          <span className="text-sm text-muted-foreground">{APP_VERSION}</span>
        </SettingsRow>

        <SettingsRow
          label="Backend status"
          description="Connection status will appear here once available."
        >
          {/* TODO: replace with a real health-check indicator once a status endpoint exists */}
          <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-muted-foreground/40" />
            Unknown
          </span>
        </SettingsRow>
      </SectionCard>

      <Separator />

      <p className="pb-4 text-center text-xs text-muted-foreground">
        Some settings are placeholders until backend integration is available.
      </p>
    </div>
  );
}