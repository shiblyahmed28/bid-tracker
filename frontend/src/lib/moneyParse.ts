/** Mirrors apps.sync.normalizers.norm_money exactly — same currency
 * detection (USD/$ vs BDT default), same comma-strip (handles Bangladeshi
 * grouping like "9,20,000.00"), same "unparseable keeps the raw text"
 * contract. Used only for the create/edit form's live preview (§11);
 * the backend re-derives nothing — the frontend submits this same parse. */
export interface ParsedMoney {
  amount: number | null;
  currency: "BDT" | "USD" | "";
}

const STRIP_RE = /[^0-9.]/g;

export function parseMoneyPreview(raw: string): ParsedMoney {
  const trimmed = raw.trim();
  if (!trimmed) return { amount: null, currency: "" };

  const currency: "BDT" | "USD" = trimmed.toUpperCase().includes("USD") || trimmed.includes("$") ? "USD" : "BDT";

  const cleaned = trimmed.replace(STRIP_RE, "");
  if (cleaned === "" || cleaned === ".") return { amount: null, currency };

  const amount = Number(cleaned);
  return Number.isNaN(amount) ? { amount: null, currency } : { amount, currency };
}

export function formatMoneyPreview(raw: string): string {
  if (!raw.trim()) return "";
  const { amount, currency } = parseMoneyPreview(raw);
  if (amount === null) return "Unparseable — kept as free text, no amount stored";
  const formatted = amount.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return `Reads as ${currency} ${formatted}`;
}
