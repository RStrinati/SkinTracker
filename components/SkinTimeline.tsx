import React, { useState, useEffect } from "react";

// Extend the Window interface to include Telegram
declare global {
  interface Window {
    Telegram?: any;
  }
}

// Simple timeline event interface
interface TimelineEvent {
  id: string;
  lane: string;
  title: string;
  start: string;
  end?: string;
  severity?: number;
  tags?: string[];
  mediaUrl?: string;
  details?: string;
  source: string;
}

interface TimelineResponse {
  events: TimelineEvent[];
  totalCount: number;
  fromDate: string;
  toDate: string;
}

interface TriggerInsight {
  triggerName: string;
  symptomName: string;
  pairCount: number;
  confidence: number;
  lift: number;
  isLikelyTrigger: boolean;
}

interface ProductEffectiveness {
  productName: string;
  nEvents: number;
  avgImprovement: number;
  effectivenessCategory: string;
}

const SkinTimeline: React.FC = () => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [insights, setInsights] = useState<{
    triggers: TriggerInsight[];
    products: ProductEffectiveness[];
  }>({
    triggers: [],
    products: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLanes, setSelectedLanes] = useState<string[]>([
    "Symptoms",
    "Products",
    "Triggers",
    "Photos",
    "Notes",
  ]);
  const [dateRange, setDateRange] = useState({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0],
    to: new Date().toISOString().split("T")[0],
  });

  // Get Telegram user ID from WebApp context or URL params
  const getTelegramUserId = (): number => {
    // Try WebApp first
    if (window.Telegram?.WebApp?.initDataUnsafe?.user?.id) {
      return window.Telegram.WebApp.initDataUnsafe.user.id;
    }

    // Fallback to URL params or demo user
    const urlParams = new URLSearchParams(window.location.search);
    return parseInt(urlParams.get("user_id") || "6865543260"); // Your demo user ID
  };

  const fetchTimelineData = async () => {
    try {
      setLoading(true);
      setError(null);
      const userId = getTelegramUserId();

      // Fetch timeline events
      const timelineParams = new URLSearchParams({
        telegram_id: userId.toString(),
        from_date: new Date(dateRange.from + "T00:00:00Z").toISOString(),
        to_date: new Date(dateRange.to + "T23:59:59Z").toISOString(),
        limit: "200",
      });

      // Add selected lanes as separate parameters
      if (selectedLanes.length > 0) {
        selectedLanes.forEach((lane) => {
          timelineParams.append("lanes", lane);
        });
      }

      console.log(
        "Fetching timeline:",
        `/api/v1/timeline/events?${timelineParams}`
      );
      const timelineResponse = await fetch(
        `/api/v1/timeline/events?${timelineParams}`
      );

      if (!timelineResponse.ok) {
        throw new Error(
          `Timeline API error: ${timelineResponse.status} ${timelineResponse.statusText}`
        );
      }

      const timelineData: TimelineResponse = await timelineResponse.json();
      setEvents(timelineData.events);

      // Fetch insights
      try {
        const triggersResponse = await fetch(
          `/api/v1/timeline/insights/triggers?telegram_id=${userId}`
        );
        const triggersData: TriggerInsight[] = triggersResponse.ok
          ? await triggersResponse.json()
          : [];

        const productsResponse = await fetch(
          `/api/v1/timeline/insights/products?telegram_id=${userId}`
        );
        const productsData: ProductEffectiveness[] = productsResponse.ok
          ? await productsResponse.json()
          : [];

        setInsights({
          triggers: triggersData,
          products: productsData,
        });
      } catch (insightError) {
        console.warn("Error fetching insights:", insightError);
        // Continue with empty insights
      }
    } catch (error) {
      console.error("Error fetching timeline data:", error);
      setError(
        error instanceof Error ? error.message : "Unknown error occurred"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimelineData();
  }, [dateRange, selectedLanes]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getSeverityColor = (severity?: number) => {
    if (!severity) return "#e5e7eb";
    const colors = ["#10b981", "#f59e0b", "#ef4444", "#dc2626", "#991b1b"];
    return colors[severity - 1] || "#e5e7eb";
  };

  const getLaneColor = (lane: string) => {
    const colors: Record<string, string> = {
      Symptoms: "#ef4444",
      Products: "#10b981",
      Triggers: "#f59e0b",
      Photos: "#8b5cf6",
      Notes: "#6b7280",
    };
    return colors[lane] || "#6b7280";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className="text-lg">Loading timeline...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-600">
          <div className="text-lg mb-2">Error loading timeline</div>
          <div className="text-sm">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 bg-white min-h-screen">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">
        Skin Health Timeline
      </h1>

      {/* Controls */}
      <div className="mb-6 space-y-4">
        {/* Date Range */}
        <div className="flex gap-4 items-center">
          <label className="text-sm font-medium">Date Range:</label>
          <input
            type="date"
            value={dateRange.from}
            onChange={(e) =>
              setDateRange((prev) => ({ ...prev, from: e.target.value }))
            }
            className="border rounded px-3 py-1"
          />
          <span>to</span>
          <input
            type="date"
            value={dateRange.to}
            onChange={(e) =>
              setDateRange((prev) => ({ ...prev, to: e.target.value }))
            }
            className="border rounded px-3 py-1"
          />
        </div>

        {/* Lane Filters */}
        <div>
          <label className="text-sm font-medium block mb-2">Show:</label>
          <div className="flex gap-2 flex-wrap">
            {["Symptoms", "Products", "Triggers", "Photos", "Notes"].map(
              (lane) => (
                <label key={lane} className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={selectedLanes.includes(lane)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedLanes((prev) => [...prev, lane]);
                      } else {
                        setSelectedLanes((prev) =>
                          prev.filter((l) => l !== lane)
                        );
                      }
                    }}
                  />
                  <span style={{ color: getLaneColor(lane) }}>{lane}</span>
                </label>
              )
            )}
          </div>
        </div>
      </div>

      {/* Timeline Events */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">
          Timeline ({events.length} events)
        </h2>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-center gap-4 p-3 border rounded-lg hover:bg-gray-50"
            >
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: getLaneColor(event.lane) }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{event.title}</span>
                  {event.severity && (
                    <span
                      className="text-xs px-2 py-1 rounded text-white"
                      style={{
                        backgroundColor: getSeverityColor(event.severity),
                      }}
                    >
                      {event.severity}/5
                    </span>
                  )}
                  <span className="text-xs text-gray-500">{event.lane}</span>
                </div>
                {event.details && (
                  <div className="text-sm text-gray-600 truncate">
                    {event.details}
                  </div>
                )}
                <div className="text-xs text-gray-400">
                  {formatDate(event.start)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Insights */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Likely Triggers */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Likely Triggers</h2>
          <div className="space-y-2">
            {insights.triggers
              .filter((t) => t.isLikelyTrigger)
              .slice(0, 5)
              .map((trigger, index) => (
                <div
                  key={index}
                  className="p-3 bg-red-50 border border-red-200 rounded-lg"
                >
                  <div className="font-medium text-red-800">
                    {trigger.triggerName} → {trigger.symptomName}
                  </div>
                  <div className="text-sm text-red-600">
                    Confidence: {(trigger.confidence * 100).toFixed(1)}% | Lift:{" "}
                    {trigger.lift.toFixed(2)}x | Occurrences:{" "}
                    {trigger.pairCount}
                  </div>
                </div>
              ))}
            {insights.triggers.filter((t) => t.isLikelyTrigger).length ===
              0 && (
              <div className="text-gray-500 text-sm">
                No strong trigger patterns detected yet.
              </div>
            )}
          </div>
        </div>

        {/* Product Effectiveness */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Product Effectiveness</h2>
          <div className="space-y-2">
            {insights.products.slice(0, 5).map((product, index) => (
              <div
                key={index}
                className={`p-3 border rounded-lg ${
                  product.effectivenessCategory === "working"
                    ? "bg-green-50 border-green-200"
                    : product.effectivenessCategory === "worsening"
                    ? "bg-red-50 border-red-200"
                    : "bg-gray-50 border-gray-200"
                }`}
              >
                <div className="font-medium">
                  {product.productName}
                  <span
                    className={`ml-2 text-xs px-2 py-1 rounded ${
                      product.effectivenessCategory === "working"
                        ? "bg-green-100 text-green-800"
                        : product.effectivenessCategory === "worsening"
                        ? "bg-red-100 text-red-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {product.effectivenessCategory}
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  Avg improvement: {product.avgImprovement > 0 ? "+" : ""}
                  {product.avgImprovement.toFixed(2)}| Events: {product.nEvents}
                </div>
              </div>
            ))}
            {insights.products.length === 0 && (
              <div className="text-gray-500 text-sm">
                Not enough data for product analysis yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SkinTimeline;
