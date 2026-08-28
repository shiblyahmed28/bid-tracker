import { useEffect, useState } from "react";

import { fetchChoiceLists } from "../api/settings";
import { ChoiceValuesPanel } from "./ChoiceValuesPanel";
import { ListsRail } from "./ListsRail";
import { ReferenceDataPanel } from "./ReferenceDataPanel";
import { buildRail, type RailItem } from "./railConfig";

function itemKey(item: RailItem): string {
  return `${item.kind}:${item.key}`;
}

export function ListsTab() {
  const [rail, setRail] = useState<RailItem[] | null>(null);
  const [selected, setSelected] = useState<RailItem | null>(null);

  useEffect(() => {
    fetchChoiceLists().then((lists) => {
      const built = buildRail(lists);
      setRail(built);
      setSelected((prev) => prev ?? built[0]);
    });
  }, []);

  function handleCountChange(count: number) {
    if (!selected) return;
    setRail((prev) =>
      prev
        ? prev.map((item) =>
            itemKey(item) === itemKey(selected) && item.kind === "choice" ? { ...item, valuesCount: count } : item
          )
        : prev
    );
  }

  if (!rail || !selected) return null;

  return (
    <div className="settings-lists">
      <ListsRail items={rail} selectedKey={itemKey(selected)} onSelect={setSelected} />
      <div className="settings-lists-panel">
        {selected.kind === "choice" ? (
          <ChoiceValuesPanel listKey={selected.key} listLabel={selected.label} onCountChange={handleCountChange} />
        ) : (
          <ReferenceDataPanel kind={selected.key} onCountChange={handleCountChange} />
        )}
      </div>
    </div>
  );
}
