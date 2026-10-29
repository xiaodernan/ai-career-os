"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Keyboard, LogOut, Monitor, Moon, Save, Sun } from "lucide-react";
import { PageHeader } from "@/components/common/page-header";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CareerProfileCard, CareerProfileMapsCard } from "@/components/settings/profile-cards";
import { MemoryCard } from "@/components/settings/memory-card";
import { PushCard } from "@/components/settings/push-card";
import { CalendarCard } from "@/components/settings/calendar-card";
import { InboundCard } from "@/components/settings/inbound-card";
import { SecurityCard } from "@/components/settings/security-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useLogout, useUser } from "@/lib/hooks/auth";
import { useLocale } from "@/lib/i18n/locale-context";
import { useUpdateProfile } from "@/lib/hooks/actions";

/** Mirrors `UpdateMeRequest`'s `@Size(min = 1, max = 120)` on the display name. */
const MAX_NAME = 120;

export default function SettingsPage() {
  const { t } = useLocale();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { data: user, isPending } = useUser();
  const logout = useLogout();
  const updateMe = useUpdateProfile();
  // `null` mirrors the server value; once the user types, it holds the edit until saved.
  const [name, setName] = React.useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [isMac, setIsMac] = React.useState(false);

  React.useEffect(() => {
    setIsMac(/Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent));
  }, []);

  const current = theme ?? "system";
  const displayName = name ?? user?.displayName ?? "";
  const nameSaveable = displayName.trim().length >= 1 && displayName !== user?.displayName;
  const saveName = React.useCallback(() => {
    if (!nameSaveable || updateMe.isPending) return;
    updateMe.mutate(
      { displayName: displayName.trim() },
      { onSuccess: () => setName(null) }
    );
  }, [displayName, nameSaveable, updateMe]);

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader title={t("settings.title")} description={t("settings.description")} />

      {/* Account */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("settings.account")}</CardTitle>
          <CardDescription>
            {t("settings.accountDescription")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isPending ? (
            <>
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-1/2" />
            </>
          ) : user ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="display-name">{t("settings.displayName")}</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="display-name"
                    value={displayName}
                    maxLength={MAX_NAME}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="off"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    loading={updateMe.isPending}
                    disabled={!nameSaveable || updateMe.isPending}
                    onClick={saveName}
                  >
                    <Save aria-hidden />
                    {t("common.save")}
                  </Button>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                  <Badge variant="outline" className="capitalize">{user.role?.toLowerCase?.() ?? "user"}</Badge>
                </div>
              </div>
              <Separator />
              <div className="flex items-center justify-between gap-4 pt-1">
                <div>
                  <p className="text-sm font-medium">{t("settings.signOut")}</p>
                  <p className="text-sm text-muted-foreground">
                    {t("settings.signOutDescription")}
                  </p>
                </div>
                <Button variant="danger" size="sm" onClick={() => setConfirmOpen(true)}>
                  <LogOut aria-hidden />
                  {t("settings.logOutConfirm")}
                </Button>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">{t("settings.sessionUnverified")}</p>
          )}
        </CardContent>
      </Card>

      {/* The second door (36.4) */}
      <SecurityCard />

      {/* Career profile */}
      <CareerProfileCard />
      <CareerProfileMapsCard />

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("settings.appearance")}</CardTitle>
          <CardDescription>{t("settings.appearanceDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={current}
            onValueChange={setTheme}
            className="grid max-w-md grid-cols-3 gap-3"
            aria-label={t("settings.colorTheme")}
          >
            {(
              [
                { value: "light", labelKey: "settings.themeLight", icon: Sun },
                { value: "dark", labelKey: "settings.themeDark", icon: Moon },
                { value: "system", labelKey: "settings.themeSystem", icon: Monitor },
              ] as const
            ).map(({ value, labelKey, icon: Icon }) => (
              <Label
                key={value}
                htmlFor={`theme-${value}`}
                className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border p-4 text-sm transition-colors duration-150 hover:bg-accent has-focus-visible:ring-[3px] has-focus-visible:ring-primary/30 ${
                  current === value ? "border-primary bg-primary/5 text-foreground" : "border-border"
                }`}
              >
                <Icon className="size-4 text-muted-foreground" aria-hidden />
                {t(labelKey)}
                <RadioGroupItem value={value} id={`theme-${value}`} className="sr-only" />
              </Label>
            ))}
          </RadioGroup>
          <p className="mt-3 text-xs text-muted-foreground" aria-live="polite">
            {t("settings.renderingIn", {
              palette:
                resolvedTheme === "dark" ? t("settings.paletteDark") : t("settings.paletteLight"),
            })}
          </p>
        </CardContent>
      </Card>

      {/* The bell outside the tab (33.4) */}
      <PushCard />

      {/* The reminders outside the app (34.1) */}
      <CalendarCard />

      {/* The address replies come back to (37.4) */}
      <InboundCard />

      {/* Keyboard */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("settings.keyboard")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-muted-foreground">
                <Keyboard className="size-4" aria-hidden /> {t("settings.commandPalette")}
              </span>
              <kbd className="rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-xs">
                {isMac ? "⌘K" : "Ctrl K"}
              </kbd>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Long-term memory — the one surface that can correct what the model believes */}
      <MemoryCard />

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={t("settings.logOut")}
        description={t("settings.logOutDescription")}
        confirmLabel={t("settings.logOutConfirm")}
        destructive
        loading={logout.isPending}
        onConfirm={() =>
          logout.mutate(undefined, { onSettled: () => setConfirmOpen(false) })
        }
      />
    </div>
  );
}
