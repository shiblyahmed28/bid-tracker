import { useEffect, useState } from "react";

import { fetchOldestPending, type DashboardSummary } from "../api/dashboard";
import { formatDMY } from "../lib/dateUtils";
import { formatBDT, formatUSD } from "../lib/money";
import { useDateRange } from "./DateRangeContext";
import { Skeleton } from "./Skeleton";

interface KpiCardsProps {
  summary: DashboardSummary | null;
  loading: boolean;
  bgExposureCount: number | null;
}

function KpiCard({
  label,
  value,
  sub,
  footer,
  footerTone,
}: {
  label: string;
  value: string | number;
  sub: string;
  footer: string;
  footerTone: "up" | "flat" | "warn";
}) {
  return (
    <div className="card kpi">
      <span className="klab">{label}</span>
      <b className="num kval">{value}</b>
      <span className="ksub">{sub}</span>
      <span className={`kfoot ${footerTone}`}>{footer}</span>
    </div>
  );
}

function KpiCardSkeleton() {
  return (
    <div className="card kpi">
      <Skeleton height={10} width={100} />
      <div style={{ marginTop: 10 }}>
        <Skeleton height={27} width={70} />
      </div>
      <div style={{ marginTop: 8 }}>
        <Skeleton height={11} width={130} />
      </div>
    </div>
  );
}

export function KpiCards({ summary, loading, bgExposureCount }: KpiCardsProps) {
  const { from, to } = useDateRange();
  const [oldestPending, setOldestPending] = useState<string | null>(null);

  useEffect(() => {
    if (!summary || summary.pending === 0) {
      setOldestPending(null);
      return;
    }
    let cancelled = false;
    fetchOldestPending({ from, to }).then((date) => {
      if (!cancelled) setOldestPending(date);
    });
    return () => {
      cancelled = true;
    };
  }, [summary, from, to]);

  if (loading || !summary) {
    return (
      <div className="grid kpis">
        <KpiCardSkeleton />
        <KpiCardSkeleton />
        <KpiCardSkeleton />
        <KpiCardSkeleton />
      </div>
    );
  }

  const submissionRate = summary.total
    ? `${Math.round((summary.submitted / summary.total) * 100)}% submission rate`
    : "—";
  const winRate = summary.win_rate_pct === null ? "—" : `${summary.win_rate_pct}%`;
  const { BDT: securityBdt, USD: securityUsd } = summary.security_live.locked;

  return (
    <div className="grid kpis">
      <KpiCard
        label="Submitted in range"
        value={summary.submitted}
        sub={`${summary.not_submitted} not submitted · ${summary.total} total`}
        footer={submissionRate}
        footerTone="up"
      />
      <KpiCard
        label="Win rate"
        value={winRate}
        sub={`${summary.won} won · ${summary.lost} lost`}
        footer={`${summary.won + summary.lost} decided`}
        footerTone="flat"
      />
      <KpiCard
        label="Awaiting result"
        value={summary.pending}
        sub="still pending in range"
        footer={summary.pending ? `oldest ${formatDMY(oldestPending)}` : "—"}
        footerTone="warn"
      />
      <KpiCard
        label="Security locked up"
        value={securityBdt ? formatBDT(securityBdt) : "—"}
        sub={`${summary.security_live.count} live guarantees${securityUsd ? " · " + formatUSD(securityUsd) : ""}`}
        footer={`${bgExposureCount ?? "—"} expiring in 60d`}
        footerTone="warn"
      />
    </div>
  );
}
