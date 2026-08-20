"use client";

import {
  Content,
  Header,
  HeaderMenuItem,
  HeaderName,
  HeaderNavigation,
  Theme,
} from "@carbon/react";
import Link from "next/link";
import { usePathname } from "next/navigation";


export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <Theme theme="white">
      <Header aria-label="ARE">
        <HeaderName as={Link} href="/" prefix="ARE">
          Analytical Reasoning Engine
        </HeaderName>
        <HeaderNavigation aria-label="ARE navigation">
          <HeaderMenuItem as={Link} href="/upload" isActive={pathname === "/upload"}>
            上傳 CSV
          </HeaderMenuItem>
          <HeaderMenuItem
            as={Link}
            href="/prompts"
            isActive={pathname?.startsWith("/prompts") ?? false}
          >
            歷史 Prompt
          </HeaderMenuItem>
        </HeaderNavigation>
      </Header>
      <Content className="are-shell">{children}</Content>
    </Theme>
  );
}
