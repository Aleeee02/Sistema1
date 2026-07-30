import { AppShell } from "@/components/layout/app-shell";

export default function PanelLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <AppShell>{children}</AppShell>;
}

