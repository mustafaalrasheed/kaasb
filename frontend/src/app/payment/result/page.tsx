"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLocale } from "@/providers/locale-provider";

type PaymentStatus = "success" | "failed" | "cancelled" | "unknown";

function PaymentResultContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const status = (searchParams.get("status") ?? "unknown") as PaymentStatus;
  const orderId = searchParams.get("order") ?? "";

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
      title: ar ? "تمت عملية الدفع بنجاح" : "Payment Successful",
      message: ar
        ? "تم تأكيد دفعة الضمان. جارٍ تحويلك إلى لوحة التحكم…"
        : "Your escrow payment was confirmed. Redirecting to your dashboard…",
      color: ar ? "text-green-700" : "text-green-700",
    },
    failed: {
      icon: (
        <div className="w-16 h-16 mx-auto rounded-full bg-red-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      ),
      title: ar ? "فشلت عملية الدفع" : "Payment Failed",
      message: ar
        ? "تعذّر معالجة دفعتك. لم يتم خصم أي مبلغ."
        : "Your payment could not be processed. No funds were charged.",
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
      title: ar ? "تم إلغاء الدفع" : "Payment Cancelled",
      message: ar
        ? "لقد ألغيت عملية الدفع. لم يتم خصم أي مبلغ."
        : "You cancelled the payment. No funds were charged.",
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
      title: ar ? "حالة غير معروفة" : "Unknown Status",
      message: ar
        ? "تعذّر تحديد حالة دفعتك. يرجى التحقق من لوحة التحكم."
        : "We could not determine your payment status. Please check your dashboard.",
      color: "text-gray-700",
    },
  };

  const c = config[status] ?? config.unknown;

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
        <div className="mb-6">{c.icon}</div>

        <h1 className={`text-2xl font-bold text-gray-900 mb-3 ${c.color}`}>{c.title}</h1>
        <p className="text-gray-600 mb-6">{c.message}</p>

        {orderId && (
          <p className="text-xs text-gray-400 mb-6 font-mono break-all">
            {ar ? "رقم الطلب: " : "Order: "}{orderId}
          </p>
        )}

        <div className="flex flex-col gap-3">
          {status === "success" && (
            <Link href="/dashboard/payments"
              className="w-full py-2.5 px-4 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors">
              {ar ? "الانتقال إلى المدفوعات" : "Go to Payments"}
            </Link>
          )}
          {(status === "failed" || status === "cancelled" || status === "unknown") && (
            <>
              <Link href="/dashboard/payments"
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                {ar ? "العودة إلى لوحة التحكم" : "Go to Dashboard"}
              </Link>
              <Link href="/dashboard"
                className="w-full py-2.5 px-4 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors">
                {ar ? "الصفحة الرئيسية" : "Home"}
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

export default function PaymentResultPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <PaymentResultContent />
    </Suspense>
  );
}
