import type { ToolCall } from "../types";
import { Icon } from "./Icon";

/** What the agent did: each tool, its arguments and its raw output (collapsed by default). */
export function ToolCalls({ calls }: { calls: ToolCall[] }) {
  if (!calls.length) return null;
  return (
    <details className="tools">
      <summary>
        <Icon name="tool" size={16} /> Tool calls ({calls.length})
      </summary>
      {calls.map((call, i) => {
        const ok = call.status === "success";
        return (
          <div key={i} className="tool" data-status={call.status}>
            <div className="tool-name">
              <span className={ok ? "ok" : "fail"} aria-label={ok ? "succeeded" : "failed"}>
                {ok ? "✅" : "❌"}
              </span>
              <code>{call.name}</code>
            </div>
            <pre className="args">{JSON.stringify(call.args, null, 2)}</pre>
            <pre className="output">{call.output}</pre>
          </div>
        );
      })}
    </details>
  );
}
