import { useNavigate } from "react-router-dom";

import type { BgExposureResponse } from "../api/dashboard";
import { daysBetween, todayISO } from "../lib/dateUtils";
import { formatBDT, formatUSD } from "../lib/money";
import { EmptyState, Skeleton } from "./Skeleton";

interface SecurityExpiringProps {
  data: BgExposureResponse | null;
  loading: boolean;
}

const MAX_ROWS = 8;

export function SecurityExpiring({ data, loading }: SecurityExpiringProps) {
  const navigate = useNavigate();
  const today = todayISO();
  const items = (data?.items ?? []).slice(0, MAX_ROWS);
  const { BDT: totalBdt, USD: totalUsd } = data?.security_locked ?? { BDT: 0, USD: 0 };

  return (
    <div className="card">
      <div className="chead">
        <h2>Bid security expiring</h2>
        <span className="scope">Next 60 days</span>
        <div className="hgap" />
        {!loading && (totalBdt > 0 || totalUsd > 0) && (
          <b className="num" style={{ color: "var(--danger)" }}>
            {[totalBdt ? formatBDT(totalBdt) : null, totalUsd ? formatUSD(totalUsd) : null]
              .filter(Boolean)
              .join(" · ")}
          </b>
        )}
      </div>
      <div className="tscroll">
        {loading ? (
          <div style={{ padding: 15 }}>
            <Skeleton height={180} />
          </div>
        ) : items.length === 0 ? (
          <EmptyState message="No guarantees expiring in the next 60 days" />
        ) : (
          <table>
            <thead>
              <tr>
                <th>Client</th>
                <th>Bank</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const countdown = daysBetween(today, item.bg_expiry_date);
                const tagClass = countdown <= 7 ? "t-lost" : countdown <= 30 ? "t-pend" : "t-no";
                return (
                  <tr key={item.id} onClick={() => navigate(`/bids/${item.id}`)} style={{ cursor: "pointer" }}>
                    <td className="trunc" style={{ maxWidth: 150 }}>
                      {item.client}
                    </td>
                    <td>{item.bg_bank || "—"}</td>
                    <td className="num" style={{ textAlign: "right" }}>
                      {item.security_amount !== null
                        ? `${item.security_currency} ${item.security_amount.toLocaleString("en-IN")}`
                        : item.security_amount_raw}
                    </td>
                    <td>
                      <span className={`tag ${tagClass}`}>{countdown === 0 ? "Today" : `${countdown}d`}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
