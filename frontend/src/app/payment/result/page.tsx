"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";

type PaymentStatus = "success" | "failed" | "cancelled" | "unknown";

export default function PaymentResultPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const status = (searchParams.get("status") ?? "unknown") as PaymentStatus;
  const orderId = searchParams.get("order") ?? "";

  // Auto-redirect to dashboard after success
  useEffect(() => {
    if (status === "success") {
      const timer = setTimeout(() => router.push("/dashboard/payments"), 4000);
      return () => clearTimeout(timer);
    }
  }, [status, router]);

  const config = {
    success: {
      icon: (
        <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      ),
      titleEn: "Payment Successful",
      titleAr: "تمت عملية الدفع بنجاح",
      messageEn: "Your escrow payment was confirmed. Redirecting to your dashboard…",
      messageAr: "تم تأكيد دفعة الضمان. جارٍ تحويلك إلى لوحة التحكم…",
      color: "text-green-700",
    },
    failed: {
      icon: (
        <div className="w-16 h-16 mx-auto rounded-full bg-red-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      ),
      titleEn: "Payment Failed",
      titleAr: "فشلت عملية الدفع",
      messageEn: "Your payment could not be processed. No funds were charged.",
      messageAr: "تعذّر معالجة دفعتك. لم يتم خصم أي مبلغ.",
      color: "text-red-700",
    },
    cancelled: {
      icon: (
        <div className="w-16 h-16 mx-auto rounded-full bg-yellow-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      ),
      titleEn: "Payment Cancelled",
      titleAr: "تم إلغاء الدفع",
      messageEn: "You cancelled the payment. No funds were charged.",
      messageAr: "لقد ألغيت عملية الدفع. لم يتم خصم أي مبلغ.",
      color: "text-yellow-700",
    },
    unknown: {
      icon: (
        <div className="w-16 h-16 mx-auto rounded-full bg-gray-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      ),
      titleEn: "Unknown Status",
      titleAr: "حالة غير معروفة",
      messageEn: "We could not determine your payment status. Please check your dashboard.",
      messageAr: "تعذّر تحديد حالة دفعتك. يرجى التحقق من لوحة التحكم.",
      color: "text-gray-700",
    },
  };

  const c = config[status] ?? config.unknown;

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
        <div className="mb-6">{c.icon}</div>

        <h1 className="text-2xl font-bold text-gray-900 mb-1">{c.titleEn}</h1>
        <h2 className={`text-lg font-medium mb-4 ${c.color}`} dir="rtl">{c.titleAr}</h2>

        <p className="text-gray-600 mb-1">{c.messageEn}</p>
        <p className="text-gray-500 text-sm mb-6" dir="rtl">{c.messageAr}</p>

        {orderId && (
          <p className="text-xs text-gray-400 mb-6 font-mono break-all">Order: {orderId}</p>
        )}

        <div className="flex flex-col gap-3">
          {status === "success" && (
            <Link
              href="/dashboard/payments"
              className="w-full py-2.5 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
            >
              الانتقال إلى المدفوعات
            </Link>
          )}
          {(status === "failed" || status === "cancelled" || status === "unknown") && (
            <>
              <Link
                href="/dashboard/payments"
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                العودة إلى لوحة التحكم
              </Link>
              <Link
                href="/dashboard"
                className="w-full py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                الصفحة الرئيسية
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
