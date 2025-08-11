'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import dynamic from 'next/dynamic';

const Charts = dynamic(() => import('../../components/Charts'), { ssr: false });

interface ProductLog {
  product_name: string;
  logged_at: string;
}

interface TriggerLog {
  trigger_name: string;
  logged_at: string;
}

interface SymptomLog {
  symptom_name: string;
  severity: number;
  logged_at: string;
}

interface UserLogs {
  products: ProductLog[];
  triggers: TriggerLog[];
  symptoms: SymptomLog[];
}

declare global {
  interface Window {
    onTelegramAuth?: (user: any) => void;
  }
}

export default function DashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [logs, setLogs] = useState<UserLogs | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem('tg-session');
    if (saved) {
      setToken(saved);
      return;
    }

    window.onTelegramAuth = (user: any) => {
      const session = JSON.stringify(user);
      window.localStorage.setItem('tg-session', session);
      setToken(session);
    };

    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.async = true;
    script.setAttribute('data-telegram-login', process.env.NEXT_PUBLIC_TELEGRAM_BOT ?? '');
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-userpic', 'false');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    document.getElementById('telegram-login')?.appendChild(script);
  }, []);

  const fetchLogs = useCallback(() => {
    fetch('/api/logs', { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.json())
      .then((data) => setLogs(data as UserLogs))
      .catch((err) => console.error('Failed to load logs', err));
  }, [token]);

  useEffect(() => {
    if (!token || logs) return;
    fetchLogs();
  }, [token, logs, fetchLogs]);

  const productData = useMemo(() => {
    if (!logs) return [] as { date: string; count: number }[];
    const counts: Record<string, number> = {};
    logs.products?.forEach((p) => {
      const date = p.logged_at.slice(0, 10);
      counts[date] = (counts[date] || 0) + 1;
    });
    return Object.entries(counts).map(([date, count]) => ({ date, count }));
  }, [logs]);

  const triggerData = useMemo(() => {
    if (!logs) return [] as { date: string; count: number }[];
    const counts: Record<string, number> = {};
    logs.triggers?.forEach((t) => {
      const date = t.logged_at.slice(0, 10);
      counts[date] = (counts[date] || 0) + 1;
    });
    return Object.entries(counts).map(([date, count]) => ({ date, count }));
  }, [logs]);

  const symptomData = useMemo(() => {
    if (!logs) return [] as { date: string; severity: number }[];
    const groups: Record<string, { total: number; count: number }> = {};
    logs.symptoms?.forEach((s) => {
      const date = s.logged_at.slice(0, 10);
      groups[date] = groups[date] || { total: 0, count: 0 };
      groups[date].total += s.severity || 0;
      groups[date].count += 1;
    });
    return Object.entries(groups).map(([date, { total, count }]) => ({
      date,
      severity: Math.round((total / count) * 100) / 100,
    }));
  }, [logs]);

  if (!token) {
    return (
      <div className="flex justify-center p-6">
        <div id="telegram-login" />
      </div>
    );
  }

  if (!logs) {
    return <div className="p-6">Loading data...</div>;
  }

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <Charts
        productData={productData}
        triggerData={triggerData}
        symptomData={symptomData}
      />
    </div>
  );
}

