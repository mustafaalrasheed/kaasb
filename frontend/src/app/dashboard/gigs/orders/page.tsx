"use client";

import { useState, useEffect, useCallback } from "react";
import { gigsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useLocale } from "@/providers/locale-provider";
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

const STATUS_LABELS_AR: Record<string, string> = {
  pending: "معلق",
  in_progress: "جارٍ",
  delivered: "مُسلَّم",
  revision_requested: "طلب مراجعة",
  completed: "مكتمل",
  cancelled: "ملغى",
  disputed: "متنازع عليه",
};

const STATUS_LABELS_EN: Record<string, string> = {
  pending: "Pending",
  in_progress: "In Progress",
  delivered: "Delivered",
  revision_requested: "Revision Requested",
  completed: "Completed",
  cancelled: "Cancelled",
  disputed: "Disputed",
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
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [tab, setTab] = useState<"selling" | "buying">("selling");
  const [orders, setOrders] = useState<GigOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const isFreelancer = user?.primary_role === "freelancer";
  const statusLabels = ar ? STATUS_LABELS_AR : STATUS_LABELS_EN;

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

  useEffect(() => {
    if (!isFreelancer) setTab("buying");
  }, [isFreelancer]);

  const handleDeliver = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      await gigsApi.markDelivered(orderId);
      toast.success(ar ? "تم تسليم الطلب" : "Order delivered");
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر تسليم الطلب" : "Failed to deliver order");
    } finally {
      setActionLoading(null);
    }
  };

  const handleComplete = async (orderId: string) => {
    if (!confirm(ar ? "هل تريد قبول التسليم وإتمام الطلب؟" : "Accept delivery and complete this order?")) return;
    setActionLoading(orderId);
    try {
      await gigsApi.completeOrder(orderId);
      toast.success(ar ? "تم إتمام الطلب" : "Order completed");
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر إتمام الطلب" : "Failed to complete order");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevision = async (orderId: string) => {
    setActionLoading(orderId);
    try {
      await gigsApi.requestRevision(orderId);
      toast.success(ar ? "تم طلب المراجعة" : "Revision requested");
      fetchOrders();
    } catch {
      toast.error(ar ? "تعذّر طلب المراجعة" : "Failed to request revision");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {ar ? "طلبات الخدمات" : "Gig Orders"}
        </h1>
        <p className="mt-1 text-gray-600">
          {ar ? "إدارة طلبات الخدمات المرسلة والمستلمة" : "Manage your sent and received gig orders"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.filter((t) => t.value === "selling" ? isFreelancer : true).map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value as "selling" | "buying")}
            className={`px-5 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.value
                ? "border-brand-500 text-brand-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {ar ? t.labelAr : t.labelEn}
          </button>
        ))}
      </div>

      {/* Orders list */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-500">
          {ar ? "جاري التحميل..." : "Loading..."}
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-lg font-medium text-gray-900">
            {ar ? "لا توجد طلبات" : "No orders found"}
          </p>
          <p className="mt-2 text-gray-500">
            {tab === "selling"
              ? (ar ? "ستظهر هنا الطلبات التي يرسلها العملاء لخدماتك." : "Orders from clients for your gigs will appear here.")
              : (ar ? "ستظهر هنا الطلبات التي اشتريتها من المستقلين." : "Gigs you've ordered from freelancers will appear here.")}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              view={tab}
              ar={ar}
              statusLabels={statusLabels}
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
  ar,
  statusLabels,
  actionLoading,
  onDeliver,
  onComplete,
  onRevision,
}: {
  order: GigOrderItem;
  view: "selling" | "buying";
  ar: boolean;
  statusLabels: Record<string, string>;
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
              {order.gig?.title ?? (ar ? "خدمة" : "Gig")}
            </span>
            <span className={`shrink-0 px-2.5 py-0.5 text-xs font-medium rounded-full border ${STATUS_COLORS[order.status] ?? "bg-gray-50 text-gray-600 border-gray-200"}`}>
              {statusLabels[order.status] ?? order.status}
            </span>
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500 mt-1">
            <span>
              {ar ? "السعر:" : "Price:"}{" "}
              <span className="font-medium text-gray-900" dir="ltr">
                {order.price_paid.toLocaleString(ar ? "ar-IQ" : "en-US")} {ar ? "د.ع" : "IQD"}
              </span>
            </span>
            <span>{ar ? `مدة التسليم: ${order.delivery_days} يوم` : `Delivery: ${order.delivery_days} day${order.delivery_days !== 1 ? "s" : ""}`}</span>
            {order.revisions_remaining >= 0 && (
              <span>{ar ? `المراجعات المتبقية: ${order.revisions_remaining}` : `Revisions left: ${order.revisions_remaining}`}</span>
            )}
            {order.due_date && (
              <span>
                {ar ? "الموعد النهائي: " : "Due: "}
                {new Date(order.due_date).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "short", day: "numeric" })}
              </span>
            )}
            <span>
              {ar ? "طُلب " : "Ordered "}
              {new Date(order.created_at).toLocaleDateString(ar ? "ar-IQ" : "en-US", { month: "short", day: "numeric" })}
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
          {view === "selling" && order.status === "in_progress" && (
            <button
              onClick={() => onDeliver(order.id)}
              disabled={isBusy}
              className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
            >
              {isBusy ? "..." : (ar ? "تسليم الطلب" : "Deliver")}
            </button>
          )}
          {view === "buying" && order.status === "delivered" && (
            <>
              <button
                onClick={() => onComplete(order.id)}
                disabled={isBusy}
                className="btn-primary py-1.5 px-4 text-sm disabled:opacity-50"
              >
                {isBusy ? "..." : (ar ? "قبول التسليم" : "Accept")}
              </button>
              {order.revisions_remaining > 0 && (
                <button
                  onClick={() => onRevision(order.id)}
                  disabled={isBusy}
                  className="btn-secondary py-1.5 px-4 text-sm disabled:opacity-50"
                >
                  {ar ? "طلب مراجعة" : "Request Revision"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
