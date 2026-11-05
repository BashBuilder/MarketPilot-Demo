import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function PageContainer({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "mx-auto w-full max-w-7xl px-md sm:px-lg lg:px-xl",
        className,
      )}
      {...props}
    />
  );
}
