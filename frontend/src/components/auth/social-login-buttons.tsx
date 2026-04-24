"use client";

import { useState, useEffect } from "react";
import { GoogleOAuthProvider, useGoogleLogin } from "@react-oauth/google";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import { getApiError } from "@/lib/utils";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const FACEBOOK_APP_ID = process.env.NEXT_PUBLIC_FACEBOOK_APP_ID || "";

// ── Google button ────────────────────────────────────────────────────────────

function GoogleLoginButton({
  role,
  onSuccess,
  termsAccepted,
}: {
  role: "client" | "freelancer";
  onSuccess: () => void;
  termsAccepted: boolean;
}) {
  const { socialLogin } = useAuthStore();
  const [loading, setLoading] = useState(false);

  const login = useGoogleLogin({
    onSuccess: async (response) => {
      setLoading(true);
      try {
        // We pass the access_token; backend will call Google userinfo endpoint
        await socialLogin("google", response.access_token, role, termsAccepted);
        onSuccess();
      } catch (err: unknown) {
        toast.error(getApiError(err, "Google login failed"));
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      toast.error("Google login was cancelled or failed");
    },
    scope: "openid email profile",
  });

  return (
    <button
      type="button"
      onClick={() => login()}
      disabled={loading || !termsAccepted}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700 disabled:opacity-50"
    >
      {loading ? (
        <span className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
      ) : (
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
      )}
      Continue with Google
    </button>
  );
}

// ── Facebook button ──────────────────────────────────────────────────────────

declare global {
  interface Window {
    FB?: {
      init: (options: object) => void;
      login: (
        callback: (response: { authResponse?: { accessToken: string } }) => void,
        options?: object
      ) => void;
    };
    fbAsyncInit?: () => void;
  }
}

function FacebookLoginButton({
  role,
  onSuccess,
  termsAccepted,
}: {
  role: "client" | "freelancer";
  onSuccess: () => void;
  termsAccepted: boolean;
}) {
  const { socialLogin } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [sdkReady, setSdkReady] = useState(false);

  useEffect(() => {
    if (!FACEBOOK_APP_ID) return;
    if (window.FB) { setSdkReady(true); return; }

    window.fbAsyncInit = () => {
      window.FB!.init({
        appId: FACEBOOK_APP_ID,
        cookie: true,
        xfbml: false,
        version: "v19.0",
      });
      setSdkReady(true);
    };

    const script = document.createElement("script");
    script.src = "https://connect.facebook.net/en_US/sdk.js";
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);
  }, []);

  const handleFacebookLogin = () => {
    if (!window.FB) { toast.error("Facebook SDK not loaded"); return; }
    setLoading(true);
    window.FB.login(
      async (response) => {
        if (response.authResponse?.accessToken) {
          try {
            await socialLogin(
              "facebook",
              response.authResponse.accessToken,
              role,
              termsAccepted,
            );
            onSuccess();
          } catch (err: unknown) {
            toast.error(getApiError(err, "Facebook login failed"));
          }
        } else {
          toast.error("Facebook login was cancelled");
        }
        setLoading(false);
      },
      { scope: "email,public_profile" }
    );
  };

  if (!FACEBOOK_APP_ID) return null;

  return (
    <button
      type="button"
      onClick={handleFacebookLogin}
      disabled={loading || !sdkReady || !termsAccepted}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700 disabled:opacity-50"
    >
      {loading ? (
        <span className="w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
      ) : (
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#1877F2">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      )}
      Continue with Facebook
    </button>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function SocialLoginButtons({
  role = "freelancer",
  onSuccess,
  // Defaults to true so existing call sites (login page) don't regress.
  // Register page passes the real checkbox state so the buttons stay
  // disabled until the user accepts the legal terms (signup-audit F1).
  termsAccepted = true,
}: {
  role?: "client" | "freelancer";
  onSuccess: () => void;
  termsAccepted?: boolean;
}) {
  if (!GOOGLE_CLIENT_ID && !FACEBOOK_APP_ID) return null;

  return (
    <div className="space-y-3">
      {GOOGLE_CLIENT_ID && (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
          <GoogleLoginButton role={role} onSuccess={onSuccess} termsAccepted={termsAccepted} />
        </GoogleOAuthProvider>
      )}
      {FACEBOOK_APP_ID && (
        <FacebookLoginButton role={role} onSuccess={onSuccess} termsAccepted={termsAccepted} />
      )}
    </div>
  );
}
