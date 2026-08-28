/** BDT display uses Cr/Lakh shorthand for large amounts and Indian digit
 * grouping otherwise — matches the mockup and common Bangladeshi usage. */
export function formatBDT(amount: number): string {
  if (amount >= 1e7) return `৳${(amount / 1e7).toFixed(2)} Cr`;
  if (amount >= 1e5) return `৳${(amount / 1e5).toFixed(1)} L`;
  return `৳${Math.round(amount).toLocaleString("en-IN")}`;
}

export function formatUSD(amount: number): string {
  return `$${Math.round(amount).toLocaleString("en-US")}`;
}
