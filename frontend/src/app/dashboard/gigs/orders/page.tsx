"use client";

import { useState, useEffect, useCallback } from "react";
import { gigsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";

interface GigOrderItem {
  id: string;
  gig_id: string;
  package_id: string;
  client_id: string;
  freelancer_id: string;
  status: string;
  requirements?: string;
  price_paid: number;
  delivery_days: number;
  revisions_remaining: number;
  due_date?: string;
  delivered_at?: string;
  completed_at?: string;
  created_at: string;
  gig?: { title: string; slug: string };
}

const STATUS_LABELS: Record<string, string> = {
  pending: "معلق",
  in_progress: "جارٍ",
  delivered: "مُسلَّم",
  revision_requested: "طلب مراجعة",
  completed: "مكتمل",
  cancelled: "ملغى",
  disputed: "متنازع عليه",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  delivered: "bg-indigo-50 text-indigo-700 border-indigo-200",
  revision_requested: "bg-orange-50 text-orange-700 border-orange-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-gray-50 text-gray-600 border-gray-200",
  disputed: "bg-red-50 text-red-700 border-red-200",
};

const TABS = [
  { value: "selling", labelAr: "طلباتي للتنفيذ", labelEn: "Selling" },
  { value: "buying", labelAr: "طلباتي المشتراة", labelEn: "Buying" },
];

export default function GigOrdersPage() {
  const { user } = useAuthStore();
  const [tab, setTab] = useState<"selling" | "buying">("selling");
  const [orders, setOrders] = useState<GigOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const isFreelancer = user?.primary_role === "freelancer";

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const res =
        tab === "selling"
          ? await gigsApi.myOrdersAsSeller()
          : await gigsApi.myOrdersAsBuyer();
      setOrders(res.data);
    } catch {
      setOrders([]);
    } finally {
      setIsLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // Set default tab based on role
  useEffect(() => {
    if (!isFreelancer) setTab("buying");
  }, [isFreelancer]);

  const handleDeliver = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      await gigsApi.markDelivered(orderId);
      toast.success("تم تسليم الطلب");
      fetchOrders();
    } catch {
      toast.error("تعذّر تسليم الطلب");
    } finally {
      setActionLoading(null);
    }
  };

  const handleComplete = async (orderId: string) => {
    if (!confirm("هل تريد قبول التسليم وإتمام الطلب؟")) return;
    setActionLoading(orderId);
    try {
      await gigsApi.completeOrder(orderId);
      toast.success("تم إتمام الطلب");
      fetchOrders();
    } catch {
      toast.error("تعذّر إتمام الطلب");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevision = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      await gigsApi.requestRevision(orderId);
      toast.success("تم طلب المراجعة");
      fetchOrders();
    } catch {
      toast.error("تعذّر طلب المراجعة");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6" dir="rtl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">طلبات الخدمات</h1>
        <p className="mt-1 text-gray-600">إدارة طلبات الخدمات المرسلة والمستلمة</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.filter((t) =>
          t.value === "selling" ? isFreelancer : true
        ).map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value as "selling" | "buying")}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.value
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.labelAr}
          </button>
        ))}
      </div>

      {/* Orders list */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-500">جاري التحميل...</div>
      ) : orders.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-medium text-gray-900">لا توجد طلبات</p>
          <p className="mt-2 text-gray-500">
            {tab === "selling"
              ? "ستظهر هنا الطلبات التي يرسلها العملاء لخدماتك."
              : "ستظهر هنا الطلبات التي اشتريتها من المستقلين."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              view={tab}
              actionLoading={actionLoading}
              onDeliver={handleDeliver}
              onComplete={handleComplete}
              onRevision={handleRevision}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function OrderCard({
  order,
  view,
  actionLoading,
  onDeliver,
  onComplete,
  onRevision,
}: {
  order: GigOrderItem;
  view: "selling" | "buying";
  actionLoading: string | null;
  onDeliver: (id: string) => void;
  onComplete: (id: string) => void;
  onRevision: (id: string) => void;
}) {
  const isBusy = actionLoading === order.id;

  return (
    <div className="card p-5">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">
              {order.gig?.title ?? "خدمة"}
            </span>
            <span
              className={`shrink-0 px-2.5 py-0.5 text-xs font-medium rounded-full border ${
                STATUS_COLORS[order.status] ?? "bg-gray-50 text-gray-600 border-gray-200"
              }`}
            >
              {STATUS_LABELS[order.status] ?? order.status}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500 mt-1">
            <span>
              السعر:{" "}
              <span className="font-medium text-gray-900">
                {order.price_paid.toLocaleString("ar-IQ")} د.ع
              </span>
            </span>
            <span>مدة التسليم: {order.delivery_days} يوم</span>
            {order.revisions_remaining >= 0 && (
              <span>المراجعات المتبقية: {order.revisions_remaining}</span>
            )}
            {order.due_date && (
              <span>
                الموعد النهائي:{" "}
                {new Date(order.due_date).toLocaleDateString("ar-IQ", {
                  month: "short",
                  day: "numeric",
                })}
              </span>
            )}
            <span>
              طُلب{" "}
              {new Date(order.created_at).toLocaleDateString("ar-IQ", {
                month: "short",
                day: "numeric",
              })}
            </span>
          </div>

          {order.requirements && (
            <p className="mt-2 text-sm text-gray-600 line-clamp-2 bg-gray-50 p-2 rounded">
              {order.requirements}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 shrink-0 flex-wrap">
          {/* Freelancer: can deliver in-progress orders */}
          {view === "selling" && order.status === "in_progress" && (
            <button
              onClick={() => onDeliver(order.id)}
              disabled={isBusy}
              className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
            >
              {isBusy ? "..." : "تسليم الطلب"}
            </button>
          )}

          {/* Client: can complete or request revision on delivered orders */}
          {view === "buying" && order.status === "delivered" && (
            <>
              <button
                onClick={() => onComplete(order.id)}
                disabled={isBusy}
                className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
              >
                {isBusy ? "..." : "قبول التسليم"}
              </button>
              {order.revisions_remaining > 0 && (
                <button
                  onClick={() => onRevision(order.id)}
                  disabled={isBusy}
                  className="btn-secondary py-1.5 px-4 text-sm disabled:opacity-50"
                >
                  طلب مراجعة
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
