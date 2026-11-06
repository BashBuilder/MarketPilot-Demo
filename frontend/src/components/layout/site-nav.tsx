"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/campaigns", label: "Campaigns", primary: false },
  { href: "/campaigns/new", label: "New campaign", primary: true },
] as const;

function isActivePath(pathname: string, href: string): boolean {
  if (href === "/campaigns") {
    return (
      pathname === href ||
      (pathname.startsWith(`${href}/`) && pathname !== "/campaigns/new")
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SiteNav() {
  const pathname = usePathname() ?? "/";

  return (
    <nav aria-label="Primary">
      <ul className="flex items-center gap-2xs">
        {navItems.map((item) => {
          const active = isActivePath(pathname, item.href);

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-label={item.label}
                aria-current={active ? "page" : undefined}
                className={cn(
                  buttonVariants({
                    variant: item.primary ? "default" : "ghost",
                    size: "default",
                  }),
                  "h-10 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  item.primary ? "w-10 px-0 sm:w-auto sm:px-sm" : "px-sm",
                  !item.primary && active && "bg-muted text-foreground",
                )}
              >
                {item.primary ? <Plus aria-hidden="true" /> : null}
                <span className={item.primary ? "hidden sm:inline" : undefined}>
                  {item.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
