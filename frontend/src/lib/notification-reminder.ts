/**
 * The application behind a reminder row of the inbox, read out of the item's key.
 *
 * The inbox's rows are episodes, not stored notifications: the backend builds each key as
 * `reminder:<application id>:<epoch of the reminder that came due>`, precisely so that moving a
 * reminder starts a new episode instead of inheriting the old one's dismissal. The screen needs
 * the id to answer the row — snooze or clear — and the key is the only field that carries it,
 * because the link is a URL and its query string is the backend's to shape.
 *
 * A key that does not parse is *not* an id: the two presses must be absent rather than pointed at
 * a guess, since a PATCH to the wrong application either 404s or silently edits something else.
 * That is also why the epoch has to be there: a reminder item is only made once a reminder exists,
 * so an empty episode means the row is not the one this screen knows how to answer.
 */

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The id in `reminder:<uuid>:<epoch>`, or null when the key is another kind or malformed. */
export function reminderApplicationId(key: string): string | null {
  const parts = key.split(":");
  if (parts.length !== 3) return null;
  const [kind, id, epoch] = parts;
  if (kind !== "reminder") return null;
  if (!UUID.test(id)) return null;
  if (!/^\d+$/.test(epoch)) return null;
  return id;
}
