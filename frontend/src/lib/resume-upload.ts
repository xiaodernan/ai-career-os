/**
 * The seam where "the upload answered" meets "the stream starts".
 *
 * `useUploadResume` resolves to whatever the backend relay handed back, and the
 * relay forwards the ai-service's body unchanged — so an upload answer can spell
 * the task id `taskId` or `task_id`, at the top level or nested under `ingest`,
 * and the resume id the same way or nested as `resume.id`. (The upload route's
 * own response shape and the nested one both exist in the wild: the smoke
 * script's capture shows the ingest task nested, while a direct call to
 * `/resumes/upload` in an integration test returned it at the top level.)
 *
 * If these readers ever mis-spell a key, the failure is silent: no `taskId`
 * state is set, the `TaskProgress` panel never mounts, and the resume lands in
 * the workspace with no live progress at all. Hence pure functions here, pinned
 * against every spelling the backend has actually used.
 */

import { pick, str } from "@/lib/api/normalize";

export function pickTaskId(raw: unknown): string | null {
  return str(raw, "taskId", "task_id") ?? str(pick(raw, "ingest"), "taskId", "task_id") ?? null;
}

export function pickResumeId(raw: unknown): string | null {
  return (
    str(raw, "resumeId", "resume_id") ??
    str(pick(raw, "resume"), "id") ??
    null
  );
}
