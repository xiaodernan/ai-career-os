"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Keyboard, LogOut, Monitor, Moon, Sun } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useLogout, useUser } from "@/lib/hooks/auth";

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { data: user, isPending } = useUser();
  const logout = useLogout();
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [isMac, setIsMac] = React.useState(false);

  React.useEffect(() => {
    setIsMac(/Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent));
  }, []);

  const current = theme ?? "system";

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader title="Settings" description="Account, appearance and keyboard preferences." />

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <CardDescription>Read live from /users/me</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isPending ? (
            <>
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-1/2" />
            </>
          ) : user ? (
            <>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium">{user.displayName}</p>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                </div>
                <Badge variant="outline" className="capitalize">{user.role?.toLowerCase?.() ?? "user"}</Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between gap-4 pt-1">
                <div>
                  <p className="text-sm font-medium">Sign out</p>
                  <p className="text-sm text-muted-foreground">Ends this session and revokes the refresh token.</p>
                </div>
                <Button variant="danger" size="sm" onClick={() => setConfirmOpen(true)}>
                  <LogOut aria-hidden />
                  Log out
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Session could not be verified.</p>
          )}
        </CardContent>
      </Card>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Appearance</CardTitle>
          <CardDescription>The interface follows your system theme by default.</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={current}
            onValueChange={setTheme}
            className="grid max-w-md grid-cols-3 gap-3"
            aria-label="Color theme"
          >
            {(
              [
                { value: "light", label: "Light", icon: Sun },
                { value: "dark", label: "Dark", icon: Moon },
                { value: "system", label: "System", icon: Monitor },
              ] as const
            ).map(({ value, label, icon: Icon }) => (
              <Label
                key={value}
                htmlFor={`theme-${value}`}
                className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors duration-150 hover:bg-accent has-focus-visible:ring-[3px] has-focus-visible:ring-primary/30 ${
                  current === value ? "border-primary bg-primary/5 text-foreground" : "border-border"
                }`}
              >
                <Icon className="size-4 text-muted-foreground" aria-hidden />
                {label}
                <RadioGroupItem value={value} id={`theme-${value}`} className="sr-only" />
              </Label>
            ))}
          </RadioGroup>
          <p className="mt-3 text-xs text-muted-foreground" aria-live="polite">
            Rendering in {resolvedTheme === "dark" ? "dark" : "light"} palette.
          </p>
        </CardContent>
      </Card>

      {/* Keyboard */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Keyboard</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted-foreground">
                <Keyboard className="size-4" aria-hidden /> Command palette
              </span>
              <kbd className="rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-xs">
                {isMac ? "⌘K" : "Ctrl K"}
              </kbd>
            </li>
          </ul>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Log out of Career OS?"
        description="Your data stays safe — this only ends the current session."
        confirmLabel="Log out"
        destructive
        loading={logout.isPending}
        onConfirm={() =>
          logout.mutate(undefined, { onSettled: () => setConfirmOpen(false) })
        }
      />
    </div>
  );
}
