import { useState } from "react";
import { createRule, deleteRule } from "../api";
import type { Rule } from "../types";

interface Props {
  rules: Rule[];
  isAdmin: boolean;
  token: string;
  onRuleChange: () => Promise<void>;
}

export function RulesPanel({ rules, isAdmin, token, onRuleChange }: Props) {
  const [deviceId, setDeviceId] = useState("");
  const [threshold, setThreshold] = useState("");

  const add = async () => {
    if (!deviceId || !threshold) return;
    await createRule(token, deviceId, parseFloat(threshold));
    setDeviceId("");
    setThreshold("");
    await onRuleChange();
  };

  const remove = async (id: number) => {
    await deleteRule(token, id);
    await onRuleChange();
  };

  return (
    <section className="panel">
      <h2>Alert Rules</h2>
      {isAdmin && (
        <div className="rule-form">
          <input
            placeholder="device_id (e.g. solar-1)"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
          />
          <input
            type="number"
            step="0.1"
            placeholder="threshold kW"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
          />
          <button onClick={add}>Add</button>
        </div>
      )}
      {rules.length === 0 ? (
        <p className="muted">No rules defined.</p>
      ) : (
        <ul className="rules">
          {rules.map((r) => (
            <li key={r.id}>
              <span>
                {r.device_id} &gt; {r.threshold} kW
              </span>
              {isAdmin && <button onClick={() => remove(r.id)}>Delete</button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
