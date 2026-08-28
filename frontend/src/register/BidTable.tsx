import { useNavigate } from "react-router-dom";

import type { BidListItem } from "../api/bids";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";
import type { ColumnDef } from "./columns";

interface BidTableProps {
  columns: ColumnDef[];
  rows: BidListItem[];
  loading: boolean;
}

const NUMERIC_KINDS = new Set(["num", "money"]);

export function BidTable({ columns, rows, loading }: BidTableProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="cbody">
        <Skeleton height={400} />
      </div>
    );
  }

  if (!rows.length) {
    return <EmptyState message="No bids match these filters" />;
  }

  return (
    <div className="tscroll tall">
      <table id="bidtable">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((bid) => (
            <tr key={bid.id}>
              {columns.map((c) => (
                <td key={c.key} className={NUMERIC_KINDS.has(c.kind) ? "num" : c.kind === "text" || c.kind === "enum" || c.kind === "list" ? "trunc" : undefined}>
                  {c.render(bid)}
                </td>
              ))}
              <td style={{ textAlign: "right" }}>
                <button className="btn btn-s btn-sm" onClick={() => navigate(`/bids/${bid.id}`)}>
                  Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
