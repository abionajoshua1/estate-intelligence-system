import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  Building2,
  User,
  AtSign,
  Mail,
  Lock,
  Eye,
  EyeOff,
  Loader2,
  ArrowRight,
  ShieldCheck,
  MapPin,
  AlertCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Decorative skyline silhouette for the hero panel. Purely presentational —
 * built from divs rather than an image asset so it themes with the app
 * (light/dark) and needs no external file.
 */
function SkylineIllustration() {
  const buildings = [
    { w: 28, h: 90, delay: 0 },
    { w: 40, h: 140, delay: 0.05 },
    { w: 24, h: 70, delay: 0.1 },
    { w: 52, h: 180, delay: 0.15 },
    { w: 32, h: 110, delay: 0.2 },
    { w: 44, h: 150, delay: 0.25 },
    { w: 26, h: 85, delay: 0.3 },
    { w: 36, h: 120, delay: 0.35 },
    { w: 48, h: 165, delay: 0.4 },
    { w: 30, h: 95, delay: 0.45 },
  ];

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 flex h-[220px] items-end justify-center gap-2 px-8 opacity-90">
      {buildings.map((b, i) => (
        <motion.div
          key={i}
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: b.h, opacity: 1 }}
          transition={{ duration: 0.8, delay: b.delay, ease: "easeOut" }}
          style={{ width: b.w }}
          className="relative rounded-t-sm bg-gradient-to-t from-cyan-400/25 to-cyan-300/5 backdrop-blur-[1px]"
        >
          {/* window lights */}
          <div className="absolute inset-0 grid grid-cols-2 gap-[3px] p-1">
            {Array.from({ length: Math.max(4, Math.floor(b.h / 18)) }).map(
              (_, wi) => (
                <span
                  key={wi}
                  className="h-[3px] rounded-[1px] bg-cyan-200/40"
                  style={{
                    opacity: (wi + i) % 3 === 0 ? 0.9 : 0.25,
                  }}
                />
              )
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/** Soft, slowly-drifting glow orbs used as ambient hero background motion. */
function AmbientGlow() {
  return (
    <>
      <motion.div
        className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl"
        animate={{ x: [0, 30, 0], y: [0, 20, 0] }}
        transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 right-0 h-96 w-96 rounded-full bg-indigo-500/20 blur-3xl"
        animate={{ x: [0, -20, 0], y: [0, -30, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
    </>
  );
}

/** Small inline error message shown under a field. */
function FieldError({ message }) {
  if (!message) return null;
  return (
    <p className="flex items-center gap-1.5 text-xs font-medium text-destructive">
      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
      {message}
    </p>
  );
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Signup() {
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { register } = useAuth();

  const updateField = (field) => (event) => {
    setFormData((prev) => ({ ...prev, [field]: event.target.value }));
    // Clear the error for this field as soon as the user edits it.
    setErrors((prev) => (prev[field] ? { ...prev, [field]: undefined } : prev));
  };

  const validate = () => {
    const nextErrors = {};

    if (!formData.firstName.trim()) {
      nextErrors.firstName = "First name is required.";
    }
    if (!formData.lastName.trim()) {
      nextErrors.lastName = "Last name is required.";
    }
    if (!formData.username.trim()) {
      nextErrors.username = "Username is required.";
    } else if (formData.username.trim().length < 3) {
      nextErrors.username = "Username must be at least 3 characters.";
    }
    if (!formData.email.trim()) {
      nextErrors.email = "Email address is required.";
    } else if (!EMAIL_PATTERN.test(formData.email.trim())) {
      nextErrors.email = "Enter a valid email address.";
    }
    if (!formData.password) {
      nextErrors.password = "Password is required.";
    } else if (formData.password.length < 8) {
      nextErrors.password = "Password must be at least 8 characters.";
    }
    if (!formData.confirmPassword) {
      nextErrors.confirmPassword = "Please confirm your password.";
    } else if (formData.confirmPassword !== formData.password) {
      nextErrors.confirmPassword = "Passwords do not match.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!validate()) return;

    setIsLoading(true);

    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        first_name: formData.firstName,
        last_name: formData.lastName,
      });

    navigate("/login");
  } catch (error) {
    console.error(error);

    if (error.response?.data) {
      setErrors(error.response.data);
    } else {
      setErrors({
        general: "Unable to create account. Please try again.",
      });
    }
  } finally {
    setIsLoading(false);
  }
};

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Left: hero panel */}
      <div className="relative hidden overflow-hidden bg-[#070a10] lg:flex lg:w-1/2 lg:flex-col lg:justify-between">
        <AmbientGlow />

        {/* subtle grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "linear-gradient(to right, #22d3ee 1px, transparent 1px), linear-gradient(to bottom, #22d3ee 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />

        <div className="relative z-10 flex items-center gap-2.5 p-10">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-400 text-slate-900">
            <Building2 className="h-5 w-5" strokeWidth={2.25} />
          </div>
          <span className="text-lg font-semibold text-slate-100">
            Estate Intelligence
          </span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="relative z-10 max-w-md px-10"
        >
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-300">
            <MapPin className="h-3.5 w-3.5" />
            Real-time property intelligence
          </div>
          <h1 className="text-3xl font-semibold leading-tight text-slate-50 sm:text-4xl">
            Join the team building
            <br /> the future of{" "}
            <span className="text-cyan-300">property operations.</span>
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-400">
            Create your account to unify residents, properties, and service
            requests into one graph-powered intelligence layer — built for
            teams who need to act faster and with more context.
          </p>

          <div className="mt-8 flex items-center gap-3 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4 text-cyan-300" />
            Secured with encrypted, role-based access
          </div>
        </motion.div>

        <div className="relative z-10 h-[220px]">
          <SkylineIllustration />
        </div>
      </div>

      {/* Right: signup form */}
      <div className="flex w-full flex-col items-center justify-center px-4 py-10 sm:px-8 lg:w-1/2">
        {/* Mobile-only brand mark (hero is hidden below lg) */}
        <div className="mb-8 flex items-center gap-2.5 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Building2 className="h-5 w-5" strokeWidth={2.25} />
          </div>
          <span className="text-base font-semibold text-foreground">
            Estate Intelligence
          </span>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="w-full max-w-sm"
        >
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="space-y-1.5">
              <CardTitle className="text-2xl font-semibold">
                Create your account
              </CardTitle>
              <CardDescription>
                Sign up for Estate Intelligence to get started.
              </CardDescription>
            </CardHeader>

            <CardContent>
              <form onSubmit={handleSubmit} noValidate className="space-y-5">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First name</Label>
                    <div className="relative">
                      <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="firstName"
                        name="firstName"
                        type="text"
                        autoComplete="given-name"
                        placeholder="Amara"
                        value={formData.firstName}
                        onChange={updateField("firstName")}
                        aria-invalid={!!errors.firstName}
                        className="pl-9"
                      />
                    </div>
                    <FieldError message={errors.firstName} />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last name</Label>
                    <div className="relative">
                      <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="lastName"
                        name="lastName"
                        type="text"
                        autoComplete="family-name"
                        placeholder="Kone"
                        value={formData.lastName}
                        onChange={updateField("lastName")}
                        aria-invalid={!!errors.lastName}
                        className="pl-9"
                      />
                    </div>
                    <FieldError message={errors.lastName} />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <div className="relative">
                    <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      placeholder="e.g. amara.kone"
                      value={formData.username}
                      onChange={updateField("username")}
                      aria-invalid={!!errors.username}
                      className="pl-9"
                    />
                  </div>
                  <FieldError message={errors.username} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email address</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      placeholder="amara@estateintel.io"
                      value={formData.email}
                      onChange={updateField("email")}
                      aria-invalid={!!errors.email}
                      className="pl-9"
                    />
                  </div>
                  <FieldError message={errors.email} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={updateField("password")}
                      aria-invalid={!!errors.password}
                      className="pl-9 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                      tabIndex={-1}
                      aria-label={
                        showPassword ? "Hide password" : "Show password"
                      }
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <FieldError message={errors.password} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm password</Label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="••••••••"
                      value={formData.confirmPassword}
                      onChange={updateField("confirmPassword")}
                      aria-invalid={!!errors.confirmPassword}
                      className="pl-9 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                      tabIndex={-1}
                      aria-label={
                        showConfirmPassword ? "Hide password" : "Show password"
                      }
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <FieldError message={errors.confirmPassword} />
                </div>

                <Button
                  type="submit"
                  className={cn("w-full gap-2")}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    <>
                      Create account
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>

              <div className="my-6 flex items-center gap-3">
                <Separator className="flex-1" />
                <span className="text-xs text-muted-foreground">OR</span>
                <Separator className="flex-1" />
              </div>

              <p className="text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link
                  to="/login"
                  className="font-medium text-primary hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </CardContent>
          </Card>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            © {new Date().getFullYear()} Estate Intelligence System. All
            rights reserved.
          </p>
        </motion.div>
      </div>
    </div>
  );
}