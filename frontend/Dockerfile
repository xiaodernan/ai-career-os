# syntax=docker/dockerfile:1
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# The API origin has to be a BUILD argument, not a runtime variable. `endpoints.ts`
# reads `process.env.NEXT_PUBLIC_API_BASE_URL` in browser code, and Next inlines every
# NEXT_PUBLIC_* value at build time -- so setting it under `environment:` in compose did
# nothing. `.dockerignore` excludes `.env.local`, so the bundle fell back to
# `http://localhost:8080/api/v1`: a deployed app whose browser called the *visitor's* own
# machine. The default matches the dev fallback; production passes the real origin.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
# The VAPID public key is a build argument for the same reason, and one reason more: it
# must be the *public half of the backend's own pair*, because the backend signs the
# wake with the private half. A browser subscribed under any other key is a browser no
# wake can reach, and the mismatch is invisible until a push is sent. Compose passes
# `APP_PUSH_VAPID_PUBLIC_KEY` here, so one variable in the deployment's `.env` covers
# both sides (33.4). Empty is a real answer: a deployment with no pair has the switch
# off, with a sentence that says so.
ARG NEXT_PUBLIC_VAPID_PUBLIC_KEY=
ENV NEXT_PUBLIC_VAPID_PUBLIC_KEY=$NEXT_PUBLIC_VAPID_PUBLIC_KEY
# NEXT_STANDALONE=1 is what makes `next build` emit `.next/standalone`. It cannot be the
# default: `next start` refuses to serve a standalone build, and the local run and the
# E2E suite both use `next start`.
RUN NEXT_STANDALONE=1 npm run build

# Runtime stage: the traced server bundle, not the build tree.
#
# `output: "standalone"` (set above, via NEXT_STANDALONE=1) makes `next build` emit
# `.next/standalone` -- a server plus exactly the production dependencies it traced.
# Copying `node_modules` instead (as this file used to) shipped all 12 devDependencies:
# the image carried vitest, playwright, eslint and tailwind, none of which run in
# production. Standalone also means `next.config.ts` is not needed at runtime -- the
# server bundle already contains the config.
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000
# Standalone excludes these two: the server is traced, static assets are not.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
# `node server.js` rather than `next start`: the standalone server is self-contained and
# reads HOSTNAME/PORT from the environment.
CMD ["node","server.js"]
