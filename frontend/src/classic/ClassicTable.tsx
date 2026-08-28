import { Link } from "react-router-dom";

import type { BidListItem } from "../api/bids";
import { formatDMY } from "../lib/dateUtils";
import { resultTagClass, submissionStatusTagClass } from "../lib/tagClass";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";

const MAX_ROWS = 25;
const HEADERS = ["SL", "Client", "Stage", "Published", "Submission", "Expiry date", "Submission", "Result", "Actions"];

interface ClassicTableProps {
  rows: BidListItem[] | null;
  totalCount: number | null;
  loading: boolean;
}

export function ClassicTable({ rows, totalCount, loading }: ClassicTableProps) {
  return (
    <div className="card">
      <div className="tscroll tall">
        <table>
          <thead>
            <tr>
              {HEADERS.map((h, i) => (
                <th key={i} style={{ background: "var(--classic)", color: "#fff" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={HEADERS.length}>
                  <Skeleton height={200} />
                </td>
              </tr>
            ) : !rows || rows.length === 0 ? (
              <tr>
                <td colSpan={HEADERS.length}>
                  <EmptyState message="No bids in this range" />
                </td>
              </tr>
            ) : (
              rows.slice(0, MAX_ROWS).map((b) => (
                <tr key={b.id}>
                  <td className="num">{b.serial ?? "—"}</td>
                  <td className="trunc" title={b.description}>
                    {b.client.name}
                  </td>
                  <td>
                    <b style={{ fontSize: 11.5 }}>{b.stage || "—"}</b>
                  </td>
                  <td className="num">{formatDMY(b.published_date)}</td>
                  <td className="num">{formatDMY(b.submission_date)}</td>
                  <td className="num">{formatDMY(b.bg_expiry_date)}</td>
                  <td>
                    <span className={`tag ${submissionStatusTagClass(b.submission_status)}`}>
                      {b.submission_status || "—"}
                    </span>
                  </td>
                  <td>
                    <span className={`tag ${resultTagClass(b.result)}`}>{b.result || "—"}</span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <Link className="btn btn-s btn-sm" to={`/bids/${b.id}`}>
                      Details
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!loading && totalCount !== null && totalCount > MAX_ROWS && (
        <div className="pager">
          <span className="rcount">
            Showing first {MAX_ROWS} of <b className="num">{totalCount}</b> — the full register is on{" "}
            <Link to="/bids">All bids</Link>.
          </span>
        </div>
      )}
    </div>
  );
}
