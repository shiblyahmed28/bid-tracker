const PAGE_SIZE_OPTIONS = [25, 50, 100, 200];

interface PagerProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

/** Numbered pager: previous, first, ellipsis, neighbours (±2), ellipsis,
 * last, next (§13). */
export function Pager({ page, pageSize, total, onPageChange, onPageSizeChange }: PagerProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, pages);

  const numbers: (number | "gap")[] = [1];
  const lo = Math.max(2, currentPage - 2);
  const hi = Math.min(pages - 1, currentPage + 2);
  if (lo > 2) numbers.push("gap");
  for (let p = lo; p <= hi; p++) numbers.push(p);
  if (hi < pages - 1) numbers.push("gap");
  if (pages > 1) numbers.push(pages);

  const showingFrom = total === 0 ? 0 : Math.min((currentPage - 1) * pageSize + 1, total);
  const showingTo = Math.min(currentPage * pageSize, total);

  return (
    <div className="pager">
      <button className="pg" disabled={currentPage === 1} onClick={() => onPageChange(Math.max(1, currentPage - 1))}>
        ‹
      </button>
      {numbers.map((entry, index) =>
        entry === "gap" ? (
          <span className="pgap" key={`gap-${index}`}>
            …
          </span>
        ) : (
          <button
            key={entry}
            className={`pg${entry === currentPage ? " on" : ""}`}
            onClick={() => onPageChange(entry)}
          >
            {entry}
          </button>
        )
      )}
      <button
        className="pg"
        disabled={currentPage === pages}
        onClick={() => onPageChange(Math.min(pages, currentPage + 1))}
      >
        ›
      </button>
      <div className="hgap" />
      <span className="rcount">
        Showing{" "}
        <b className="num">
          {showingFrom}–{showingTo}
        </b>{" "}
        of <b className="num">{total}</b>
      </span>
      <select
        className="inp"
        style={{ width: "auto", padding: "5px 8px" }}
        value={pageSize}
        onChange={(e) => onPageSizeChange(Number(e.target.value))}
      >
        {PAGE_SIZE_OPTIONS.map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <span className="rcount">per page</span>
    </div>
  );
}
