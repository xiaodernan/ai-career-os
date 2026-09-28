"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface AuthFieldProps extends Omit<React.ComponentProps<"input">, "id"> {
  id: string;
  label: string;
  /** The message under the field; `undefined` renders no message and no error wiring. */
  error?: string;
}

/**
 * One labelled field of an auth screen: label, input, and the message beneath it.
 *
 * Sign-in, sign-up and the two recovery screens all need the same three parts, and the part
 * worth writing once is the pairing between the message and the input —
 * `aria-invalid` plus `aria-describedby` pointing at the message's id. Four copies of that
 * is four chances to drop the `aria-describedby` and leave a screen reader announcing an
 * invalid field with no reason.
 */
export function AuthField({ id, label, error, ...props }: AuthFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
