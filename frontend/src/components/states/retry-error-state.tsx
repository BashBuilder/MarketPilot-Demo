"use client";

import { useRouter } from "next/navigation";
import { ErrorState } from "./error-state";

interface RetryErrorStateProps {
  title: string;
  description: string;
}

export function RetryErrorState({
  title,
  description,
}: RetryErrorStateProps) {
  const router = useRouter();

  return (
    <ErrorState
      title={title}
      description={description}
      onRetry={() => router.refresh()}
    />
  );
}
