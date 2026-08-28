/** Up to two initials from a full name, falling back to the email's local
 * part when no name is set yet (profile avatars, §14). */
export function initials(fullName: string, email: string): string {
  const source = fullName.trim() || email.split("@")[0];
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
