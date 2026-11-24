"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Hint } from "@/components/ui/hint";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * ConfirmDialog — destructive-aware confirmation with a loading confirm button.
 *
 * The buttons read their words through the locale, so a confirmation still says
 * the reader's own language when the reader switched away from the default.
 */
export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  cancelHint?: string;
  confirmHint?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  cancelHint,
  confirmHint,
  destructive = false,
  loading = false,
  onConfirm,
}: ConfirmDialogProps) {
  const { t } = useLocale();
  const resolvedConfirmLabel = confirmLabel ?? t("common.confirm");
  const resolvedCancelLabel = cancelLabel ?? t("common.cancel");
  const resolvedCancelHint = cancelHint ?? t("common.hintCancelDialog");
  const resolvedConfirmHint = confirmHint ?? t("common.hintConfirmDialog");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-base">{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Hint anchor="span" label={resolvedCancelHint}>
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading} aria-label={t("common.close")} title={t("common.close")}>
              {resolvedCancelLabel}
            </Button>
          </Hint>
          <Hint anchor="span" label={resolvedConfirmHint}>
            <Button
              variant={destructive ? "danger" : "primary"}
              onClick={onConfirm}
              loading={loading}
            >
              {resolvedConfirmLabel}
            </Button>
          </Hint>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
