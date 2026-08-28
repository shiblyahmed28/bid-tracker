import { useId } from "react";

interface ComboInputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  required?: boolean;
  placeholder?: string;
}

/** A "searchable select with an add-new option" (§11) — a native <input>
 * wired to a <datalist> of existing values. The browser shows matching
 * suggestions as the user types, but any typed value is accepted as-is on
 * submit, which is exactly what "add new" means here: the server resolves
 * an unrecognized name into a brand new Client/Person (apps.sync.resolvers),
 * same as the sync pipeline does for the sheet. */
export function ComboInput({ label, value, onChange, options, required, placeholder }: ComboInputProps) {
  const listId = useId();

  return (
    <div className="field">
      <label className={required ? "req" : undefined}>{label}</label>
      <input
        className="inp"
        list={listId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        autoComplete="off"
      />
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </div>
  );
}
