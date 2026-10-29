import { useEffect, useState } from "react";
import { useClient } from "../api/ClientContext";
import { HEALTH_POLL_MS } from "../config";

/** `null` while the first check runs, then whether the backend answers. */
export function useHealth(intervalMs = HEALTH_POLL_MS): boolean | null {
  const client = useClient();
  const [online, setOnline] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const check = async () => {
      const ok = await client.isHealthy();
      if (alive) setOnline(ok);
    };
    void check();
    const id = window.setInterval(() => void check(), intervalMs);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [client, intervalMs]);
  return online;
}
