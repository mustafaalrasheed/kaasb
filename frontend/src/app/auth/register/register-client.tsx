"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";

export default function RegisterClient() {
  const router = useRouter();
  const { register } = useAuthStore();
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email: "",
    password: "",
    primary_role: "freelancer" as "client" | "freelancer",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };

    // Auto-suggest username from first + last name (no spaces, lowercase)
    if (name === "first_name" || name === "last_name") {
      const first = name === "first_name" ? value : formData.first_name;
      const last = name === "last_name" ? value : formData.last_name;
      if (!formData.username || formData.username === autoUsername(formData.first_name, formData.last_name)) {
        updated.username = autoUsername(first, last);
      }
    }

    // Strip spaces from username as user types
    if (name === "username") {
      updated.username = value.replace(/\s/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
    }

    setFormData(updated);
  };

  function autoUsername(first: string, last: string): string {
    return `${first}_${last}`.toLowerCase().replace(/\s/g, "_").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 30);
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await register(formData);
      router.push("/dashboard");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Pydantic validation errors — extract clear messages
        const messages = detail.map((d: any) => {
          const field = d.loc?.[d.loc.length - 1] || "field";
          const msg = d.msg?.replace("Value error, ", "") || "Invalid value";
          return `${field}: ${msg}`;
        });
        setError(messages.join("\n"));
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Registration failed. Check your inputs and try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">
              Create your account
            </h1>
            <p className="mt-2 text-gray-600">
              Join Kaasb and start your freelancing journey
            </p>
          </div>

          {error && (
            <div className="mb-6 p-3 bg-danger-50 text-danger-700 rounded-lg text-sm whitespace-pre-line">
              {error}
            </div>
          )}

          {/* Role Selection */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              I want to:
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() =>
                  setFormData({ ...formData, primary_role: "freelancer" })
                }
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  formData.primary_role === "freelancer"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-2xl mb-1">💼</div>
                <div className="font-medium text-sm">Work as Freelancer</div>
              </button>
              <button
                type="button"
                onClick={() =>
                  setFormData({ ...formData, primary_role: "client" })
                }
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  formData.primary_role === "client"
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-2xl mb-1">🏢</div>
                <div className="font-medium text-sm">Hire Freelancers</div>
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label
                  htmlFor="first_name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  First Name
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={handleChange}
                  className="input-field"
                  required
                />
              </div>
              <div>
                <label
                  htmlFor="last_name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Last Name
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={handleChange}
                  className="input-field"
                  required
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                className="input-field"
                placeholder="e.g. almustafa_abed"
                pattern="^[a-zA-Z0-9_-]+$"
                minLength={3}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Letters, numbers, underscores and hyphens only — no spaces
              </p>
            </div>

            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                className="input-field"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                className="input-field"
                placeholder="Min 8 chars, uppercase, digit, special"
                minLength={8}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Must include uppercase letter, number, and special character
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3 mt-2"
            >
              {isLoading ? "Creating account..." : "Create Account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-600">
            Already have an account?{" "}
            <Link
              href="/auth/login"
              className="text-brand-500 hover:text-brand-600 font-medium"
            >
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
