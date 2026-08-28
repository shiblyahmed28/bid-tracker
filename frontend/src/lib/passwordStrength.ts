export interface PasswordStrength {
  percent: 0 | 25 | 50 | 75 | 100;
  color: string;
  message: string;
}

const LEVELS: PasswordStrength[] = [
  { percent: 0, color: "#EFF2ED", message: "Use at least 10 characters with a mix of letters, numbers and symbols." },
  { percent: 25, color: "#C4453A", message: "Weak — too easy to guess." },
  { percent: 50, color: "#D89B2C", message: "Fair — add numbers or symbols." },
  { percent: 75, color: "#8FC157", message: "Good." },
  { percent: 100, color: "#2E6130", message: "Strong." },
];

/** Same scoring as the mockup's pwmeter(): one point each for length>=10,
 * mixed case, a digit and a symbol. Purely a UI nudge — the server only
 * enforces the 10-character minimum (§14). */
export function passwordStrength(value: string): PasswordStrength {
  if (!value) return LEVELS[0];
  let score = 0;
  if (value.length >= 10) score++;
  if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score++;
  if (/\d/.test(value)) score++;
  if (/[^A-Za-z0-9]/.test(value)) score++;
  return LEVELS[score] ?? LEVELS[0];
}
