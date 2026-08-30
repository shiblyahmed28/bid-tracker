import { useState } from "react";

import { downloadBidsCsv } from "../api/exports";
import { DateRangeProvider, useDateRange } from "../dashboard/DateRangeContext";
import { RangeBar } from "../dashboard/RangeBar";
import { formatDMY } from "../lib/dateUtils";
import { useDebouncedValue } from "../lib/useDebouncedValue";
import { ActiveFilterChips, labelFor } from "../register/ActiveFilterChips";
import { BidTable } from "../register/BidTable";
import { COLUMNS } from "../register/columns";
import { ColumnPicker } from "../register/ColumnPicker";
import { FilterPanel } from "../register/FilterPanel";
import { Pager } from "../register/Pager";
import { PdfExportDialog } from "../register/PdfExportDialog";
import { RegisterBreakdownCharts } from "../register/RegisterBreakdownCharts";
import { useBidsQuery } from "../register/useBidsQuery";
import { useColumnPreferences } from "../register/useColumnPreferences";
import { useEnumOptions } from "../register/useEnumOptions";

const DEFAULT_PAGE_SIZE = 50;

function RegisterContent() {
  const { from, to } = useDateRange();
  const { visibleKeys, toggleColumn, selectAll, resetToDefault } = useColumnPreferences();

  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [showColumns, setShowColumns] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showPdfDialog, setShowPdfDialog] = useState(false);

  const debouncedSearch = useDebouncedValue(searchInput);
  const debouncedFilters = useDebouncedValue(filters);

  const activeFilterCount = Object.values(filters).filter(Boolean).length;
  const enumOptions = useEnumOptions(showFilters || activeFilterCount > 0);

  const { data, loading } = useBidsQuery({
    from,
    to,
    search: debouncedSearch,
    filters: debouncedFilters,
    page,
    pageSize,
  });

  function updateFilter(param: string, value: string) {
    setFilters((prev) => {
      const next = { ...prev };
      if (value) next[param] = value;
      else delete next[param];
      return next;
    });
    setPage(1);
  }

  function clearAll() {
    setFilters({});
    setSearchInput("");
    setPage(1);
  }

  const visibleColumns = COLUMNS.filter((c) => visibleKeys.includes(c.key));

  const exportParams = {
    submission_after: from,
    submission_before: to,
    search: debouncedSearch || undefined,
    ...debouncedFilters,
  };
  const filterChipLabels = Object.entries(filters)
    .filter(([, value]) => value)
    .map(([param, value]) => labelFor(param, value, enumOptions));

  const filterSummary = [
    `Dates: ${formatDMY(from)} → ${formatDMY(to)}`,
    ...(debouncedSearch ? [`Search: "${debouncedSearch}"`] : []),
    ...filterChipLabels,
  ].join(" · ");

  return (
    <>
      <div className="card">
        <div className="cbody">
          <div className="tools">
            <input
              className="inp"
              style={{ flex: 1, minWidth: 190 }}
              placeholder="Search client, description, tender ID, bid manager…"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
                setPage(1);
              }}
            />
            <button className={`btn btn-s${showColumns ? " actv" : ""}`} onClick={() => setShowColumns((v) => !v)}>
              Columns <b className="num">{visibleKeys.length}</b>/{COLUMNS.length}
            </button>
            <button
              className={`btn btn-s${showFilters || activeFilterCount ? " actv" : ""}`}
              onClick={() => setShowFilters((v) => !v)}
            >
              Filters{activeFilterCount ? <> <b className="num">{activeFilterCount}</b></> : null}
            </button>
            {(activeFilterCount > 0 || searchInput) && (
              <button className="btn btn-s" onClick={clearAll}>
                Clear
              </button>
            )}
            <button className="btn btn-s" onClick={() => downloadBidsCsv({ ...exportParams, columns: visibleKeys.join(",") })}>
              Export CSV
            </button>
            <button className="btn btn-p" onClick={() => setShowPdfDialog(true)}>
              Download PDF
            </button>
          </div>

          {showColumns && (
            <ColumnPicker
              visibleKeys={visibleKeys}
              onToggle={toggleColumn}
              onSelectAll={selectAll}
              onResetToDefault={resetToDefault}
            />
          )}

          {showFilters && <FilterPanel filters={filters} options={enumOptions} onChange={updateFilter} />}
        </div>
      </div>

      <RangeBar matchedCount={data?.count ?? null} />

      <div className="card">
        <div className="chead">
          <h2>Bid register</h2>
          <span className="scope">{visibleColumns.length} columns</span>
          <div className="hgap" />
          <ActiveFilterChips
            filters={filters}
            options={enumOptions}
            onRemove={(param) => updateFilter(param, "")}
            onClearAll={() => {
              setFilters({});
              setPage(1);
            }}
          />
        </div>
        <BidTable columns={visibleColumns} rows={data?.results ?? []} loading={loading} />
        {!loading && (
          <Pager
            page={page}
            pageSize={pageSize}
            total={data?.count ?? 0}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        )}
      </div>

      <RegisterBreakdownCharts params={exportParams} filterSummary={filterSummary} />

      <PdfExportDialog
        open={showPdfDialog}
        onClose={() => setShowPdfDialog(false)}
        matchedCount={data?.count ?? null}
        exportParams={exportParams}
        filterChipLabels={filterChipLabels}
        from={from}
        to={to}
        initialColumnKeys={visibleKeys}
      />
    </>
  );
}

export function BidsPage() {
  return (
    <DateRangeProvider>
      <RegisterContent />
    </DateRangeProvider>
  );
}
