"use client";

import * as React from "react";
import { Bell } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  ensurePushRegistration,
  forgetPushSubscription,
  useRegisterPushSubscription,
} from "@/lib/hooks/push";
import {
  disablePush,
  enablePush,
  pushConfigured,
  pushPublicKey,
  readPushState,
  type EnableFailure,
  type PushState,
} from "@/lib/push";

/**
 * The one switch that turns a browser into a bell (roadmap 33.4).
 *
 * Everything the switch shows is a fact the browser answered: whether it can push at
 * all, whether the app's worker is installed, whether the reader denied the permission,
 * and whether a subscription exists. The card therefore does not keep an `on` of its
 * own -- after every attempt it re-reads the browser rather than assuming the result,
 * because "subscribe succeeded" and "the account kept the row" are two different
 * answers, and only the second one means the morning can ring.
 *
 * A registration that fails on the server is rolled back locally. Leaving the browser
 * subscribed would put `on` on the screen for a row the account never kept, and the
 * reader would wait for a ring that could not come. Opting out is the mirror image: the
 * browser unsubscribes first, then the row is deleted, and a row that is already gone is
 * not an error.
 */
export function PushCard() {
  const { t } = useLocale();
  const [state, setState] = React.useState<PushState | "loading">("loading");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const register = useRegisterPushSubscription();

  const configured = pushConfigured();
  const key = pushPublicKey();

  React.useEffect(() => {
    let alive = true;
    void readPushState().then((next) => {
      if (!alive) return;
      setState(next);
      // A subscription the account does not know about is a bell with no wire: repair
      // the row silently, since the reader already asked for this browser to ring.
      if (next.kind === "on") {
        void ensurePushRegistration(next.subscription).catch(() => undefined);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  const toggle = React.useCallback(
    async (next: boolean) => {
      if (busy || state === "loading") return;
      setBusy(true);
      setError(null);
      try {
        if (next) {
          const result = await enablePush({ key });
          if (!result.ok) {
            setState(await readPushState());
            setError(reasonKey(result.reason));
            return;
          }
          try {
            await register.mutateAsync(result.subscription);
          } catch {
            // The browser must not stay subscribed to a row the account never kept.
            await disablePush();
            setState(await readPushState());
            setError("push.failed");
            return;
          }
          setState({ kind: "on", subscription: result.subscription });
          return;
        }

        const forgotten = await disablePush();
        if (!forgotten.ok) {
          setState(await readPushState());
          setError("push.failed");
          return;
        }
        if (forgotten.endpoint) {
          // Best effort: the browser has already unsubscribed, so a row left behind is
          // retired by the push service's 410 rather than ringing anybody.
          await forgetPushSubscription(forgotten.endpoint).catch(() => undefined);
        }
        setState(await readPushState());
      } finally {
        setBusy(false);
      }
    },
    [busy, key, register, state]
  );

  const checked = state !== "loading" && state.kind === "on";
  const disabled =
    busy ||
    state === "loading" ||
    !configured ||
    state.kind === "unsupported" ||
    state.kind === "no-worker" ||
    state.kind === "blocked";

  const status = error ?? statusKey(state, configured);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("push.title")}</CardTitle>
        <CardDescription>{t("push.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <Label htmlFor="push-toggle" className="flex items-center gap-2">
              <Bell className="size-4 text-muted-foreground" aria-hidden />
              {t("push.toggle")}
            </Label>
            <p
              className={`text-sm ${error ? "text-danger" : "text-muted-foreground"}`}
              aria-live="polite"
            >
              {status ? t(status) : null}
            </p>
          </div>
          <Switch
            id="push-toggle"
            checked={checked}
            disabled={disabled}
            onCheckedChange={(next) => void toggle(next)}
            aria-label={t("push.toggle")}
          />
        </div>
      </CardContent>
    </Card>
  );
}

/** Why a switch-on did not happen, in the reader's language. */
function reasonKey(reason: EnableFailure): string {
  switch (reason) {
    case "denied":
      return "push.permissionDenied";
    case "no-worker":
      return "push.notInstalled";
    case "unsupported":
      return "push.unsupported";
    case "unconfigured":
      return "push.notConfigured";
    default:
      return "push.failed";
  }
}

/**
 * The sentence under the switch. The order is the order the browser's facts bind:
 * a browser that cannot push says nothing about a deployment's keys, and a deployment
 * without keys says nothing about a permission the reader could grant later.
 */
function statusKey(state: PushState | "loading", configured: boolean): string {
  if (state === "loading") return "push.checking";
  if (state.kind === "unsupported") return "push.unsupported";
  if (state.kind === "no-worker") return "push.notInstalled";
  if (!configured) return "push.notConfigured";
  if (state.kind === "blocked") return "push.blocked";
  if (state.kind === "on") return "push.onDescription";
  return "push.offDescription";
}
