interface ToggleRowProps {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}

export function ToggleRow({ label, hint, checked, onChange }: ToggleRowProps) {
  return (
    <div className="trow">
      <div className="tn">
        {label}
        {hint && <small>{hint}</small>}
      </div>
      <div
        className={`toggle ${checked ? "on" : ""}`}
        role="switch"
        aria-checked={checked}
        tabIndex={0}
        onClick={() => onChange(!checked)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onChange(!checked);
          }
        }}
      />
    </div>
  );
}
