"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api/client";
import { tokenStore } from "@/lib/api/token-store";

export function useUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    staleTime: 5 * 60_000,
    retry: false,
  });
}

export function useLogin() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (user) => {
      qc.setQueryData(["me"], user);
      const params = new URLSearchParams(
        typeof window !== "undefined" ? window.location.search : "",
      );
      router.replace(params.get("next") || "/dashboard");
    },
  });
}

export function useRegister() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: authApi.register,
    onSuccess: (user) => {
      qc.setQueryData(["me"], user);
      router.replace("/dashboard");
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => authApi.logout().catch(() => undefined),
    onSettled: () => {
      tokenStore.clear();
      qc.clear();
      router.replace("/login");
    },
  });
}
