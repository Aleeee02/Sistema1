"use client";

import { useEffect, useState } from "react";

export function usePermissions() {
  const [permissions, setPermissions] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/auth/me", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((session) => setPermissions(session?.permisos ?? []))
      .catch(() => setPermissions([]));
  }, []);

  return {
    permissions,
    can: (permission: string) => permissions.includes(permission),
  };
}
