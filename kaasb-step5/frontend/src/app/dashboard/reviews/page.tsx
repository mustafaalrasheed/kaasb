"use client";

import { useState, useEffect, useCallback } from "react";
import { reviewsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { toast } from "sonner";
import type { ReviewDetail, ReviewStats } from "@/types/review";
import { RATING_LABELS } from "@/types/review";

export default function ReviewsPage() {
  const { user } = useAuthStore();
  const [reviews, setReviews] = useState<ReviewDetail[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    if (!user) return;
    try {
      setLoading(true);
      const [reviewsRes, statsRes] = await Promise.all([
        reviewsApi.getUserReviews(user.id, { page, page_size: 10 }),
        reviewsApi.getUserStats(user.id),
      ]);
      setReviews(reviewsRes.data.reviews);
      setTotal(reviewsRes.data.total);
      setStats(statsRes.data);
    } catch {
      toast.error("Failed to load reviews");
    } finally {
      setLoading(false);
    }
  }, [user, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const StarDisplay = ({ rating }: { rating: number }) => (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          className={`text-sm ${i <= rating ? "text-yellow-400" : "text-gray-300"}`}
        >
          ★
        </span>
      ))}
    </div>
  );

  if (loading && !stats) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-32 bg-gray-100 rounded-lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">My Reviews</h1>

      {/* Stats Overview */}
      {stats && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Overall Rating */}
            <div className="text-center">
              <div className="text-5xl font-bold text-gray-900">
                {stats.average_rating.toFixed(1)}
              </div>
              <StarDisplay rating={Math.round(stats.average_rating)} />
              <p className="text-sm text-gray-500 mt-1">
                {stats.total_reviews} review{stats.total_reviews !== 1 ? "s" : ""}
              </p>
            </div>

            {/* Distribution */}
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((star) => {
                const count = stats.rating_distribution[String(star)] || 0;
                const pct = stats.total_reviews > 0
                  ? (count / stats.total_reviews) * 100
                  : 0;
                return (
                  <div key={star} className="flex items-center gap-2 text-sm">
                    <span className="w-8 text-right text-gray-600">{star}★</span>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-400 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-8 text-gray-400">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Category Ratings */}
          {(stats.avg_communication || stats.avg_quality || stats.avg_professionalism || stats.avg_timeliness) && (
            <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-2 md:grid-cols-4 gap-4">
              {stats.avg_communication && (
                <CategoryRating label="Communication" value={stats.avg_communication} />
              )}
              {stats.avg_quality && (
                <CategoryRating label="Quality" value={stats.avg_quality} />
              )}
              {stats.avg_professionalism && (
                <CategoryRating label="Professionalism" value={stats.avg_professionalism} />
              )}
              {stats.avg_timeliness && (
                <CategoryRating label="Timeliness" value={stats.avg_timeliness} />
              )}
            </div>
          )}
        </div>
      )}

      {/* Reviews List */}
      <div className="space-y-4">
        {reviews.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            No reviews yet. Complete contracts to receive reviews.
          </div>
        ) : (
          reviews.map((review) => (
            <div
              key={review.id}
              className="bg-white border border-gray-200 rounded-lg p-5"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-sm font-medium">
                    {review.reviewer.first_name[0]}
                    {review.reviewer.last_name[0]}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">
                      {review.reviewer.first_name} {review.reviewer.last_name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {review.contract.title}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <StarDisplay rating={review.rating} />
                  <div className="text-xs text-gray-400 mt-1">
                    {RATING_LABELS[review.rating]}
                  </div>
                </div>
              </div>
              {review.comment && (
                <p className="mt-3 text-gray-700 text-sm leading-relaxed">
                  {review.comment}
                </p>
              )}
              <div className="mt-3 text-xs text-gray-400">
                {new Date(review.created_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {total > 10 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {Math.ceil(total / 10)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 10)}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function CategoryRating({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <div className="text-lg font-semibold text-gray-900">{value.toFixed(1)}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
