"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";

type PaymentStatus = "verifying" | "SUCCESS" | "FAILED" | "PENDING" | "error";

interface VerifyResponse {
  status: "SUCCESS" | "FAILED" | "PENDING";
  message: string;
}

export default function PaymentResultPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Qi Card appends paymentId to the finishPaymentUrl
  const paymentId =
    searchParams.get("paymentId") ||
    searchParams.get("payment_id") ||
    searchParams.get("id") ||
    "";

  const [status, setStatus] = useState<PaymentStatus>("verifying");
  const [message, setMessage] = useState("Verifying your payment…");

  useEffect(() => {
    if (!paymentId) {
      setStatus("error");
      setMessage("No payment reference found in URL. Please contact support.");
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch(
          `/api/v1/payments/qi-card/verify?payment_id=${encodeURIComponent(paymentId)}`,
          { method: "GET", headers: { "Content-Type": "application/json" } }
        );

        if (!res.ok) {
          setStatus("error");
          setMessage("Failed to verify payment. Please contact support.");
          return;
        }

        const data: VerifyResponse = await res.json();
        setStatus(data.status);
        setMessage(data.message);

        // Auto-redirect on success after 3 seconds
        if (data.status === "SUCCESS") {
          setTimeout(() => router.push("/dashboard/payments"), 3000);
        }
      } catch {
        setStatus("error");
        setMessage("Network error while verifying payment. Please check your dashboard.");
      }
    };

    verify();
  }, [paymentId, router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
        {/* Icon */}
        <div className="mb-6">
          {status === "verifying" && (
            <div className="w-16 h-16 mx-auto rounded-full bg-blue-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            </div>
          )}
          {status === "SUCCESS" && (
            <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}
          {(status === "FAILED" || status === "error") && (
            <div className="w-16 h-16 mx-auto rounded-full bg-red-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          )}
          {status === "PENDING" && (
            <div className="w-16 h-16 mx-auto rounded-full bg-yellow-100 flex items-center justify-center">
              <svg className="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          )}
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {status === "verifying" && "Verifying Payment"}
          {status === "SUCCESS" && "Payment Successful"}
          {status === "FAILED" && "Payment Failed"}
          {status === "PENDING" && "Payment Pending"}
          {status === "error" && "Verification Error"}
        </h1>

        {/* Arabic title */}
        <h2 className="text-lg text-gray-600 mb-4 font-arabic" dir="rtl">
          {status === "verifying" && "جارٍ التحقق من الدفع"}
          {status === "SUCCESS" && "تمت عملية الدفع بنجاح"}
          {status === "FAILED" && "فشلت عملية الدفع"}
          {status === "PENDING" && "الدفع قيد المعالجة"}
          {status === "error" && "خطأ في التحقق"}
        </h2>

        {/* Message */}
        <p className="text-gray-600 mb-6">{message}</p>

        {/* Payment reference */}
        {paymentId && (
          <p className="text-xs text-gray-400 mb-6 font-mono">
            Ref: {paymentId}
          </p>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-3">
          {status === "SUCCESS" && (
            <>
              <p className="text-sm text-green-600">Redirecting to your dashboard…</p>
              <Link
                href="/dashboard/payments"
                className="w-full py-2.5 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
              >
                Go to Payments Dashboard
              </Link>
            </>
          )}

          {(status === "FAILED" || status === "error") && (
            <>
              <Link
                href="/dashboard/payments"
                className="w-full py-2.5 px-4 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                Return to Dashboard
              </Link>
              <Link
                href="/support"
                className="w-full py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Contact Support
              </Link>
            </>
          )}

          {status === "PENDING" && (
            <>
              <button
                onClick={() => window.location.reload()}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Check Again
              </button>
              <Link
                href="/dashboard/payments"
                className="w-full py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Go to Dashboard
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
