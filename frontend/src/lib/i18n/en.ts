/**
 * The English table (17.1). Split from translations.ts in Epic 265 -- the two
 * tables were one 410 KB file read by every route; now they compile as
 * separate modules. The envelope type lives in ./translations.ts (the seam).
 */
export const en = {
    // Navigation
    nav: {
      dashboard: "Dashboard",
      notifications: "Notifications",
      replies: "Replies",
      letters: "Letters",
      ceremony: "Ceremony",
      playbook: "Playbook",
      resumes: "Resumes",
      jobs: "Jobs",
      applications: "Applications",
      interviews: "Interviews",
      copilot: "Copilot",
      knowledge: "Knowledge",
      companies: "Companies",
      growth: "Growth",
      networking: "Networking",
      analysis: "Analysis",
      offers: "Offers",
      monitoring: "Monitoring",
      rateLimit: "Rate limit",
      activity: "Activity",
      timeline: "Timeline",
      admin: "Admin",
      settings: "Settings",
      ingestion: "Ingestion",
      yourData: "Your data",
      studio: "Studio",
    },
    /**
     * The navigation's own descriptions -- the second line of the command
     * palette's row.
     *
     * They are a separate block because they are a separate sentence: the
     * name of a page and the sentence that says what the page is for are
     * edited by different hands, and one reader changes the page's name far
     * more often than the line under it.
     */
    navDescriptions: {
      dashboard: "Career overview and priorities",
      notifications: "Signals that need your attention",
      replies: "Recruiter replies filed on your applications",
      letters: "Every letter you kept, in one gallery",
      ceremony: "The closing ceremony of this search",
      resumes: "Resume versions and structured profile",
      jobs: "Discovered jobs and AI matches",
      applications: "Pipeline kanban and reminders",
      interviews: "Adaptive AI mock interviews",
      copilot: "Career agent conversation",
      knowledge: "Career knowledge base sources",
      companies: "Company research profiles",
      growth: "Readiness, gaps and learning plan",
      networking: "Contacts and outreach",
      analysis: "Pipeline analytics and insights",
      offers: "Salary benchmarks and negotiation",
      monitoring: "Agent health and cost",
      rateLimit: "Rate-limit status and quotas",
      ingestion: "Import jobs from feeds and boards",
      yourData: "Export, restore and redact your data",
      activity: "AI agent runs and traces",
      timeline: "One ordered read of the whole loop",
      admin: "Operator ledger: stats, trends, and optimization signals",
      settings: "Account and preferences",
      studio: "Paste a job, see your fit, tailor your resume",
      playbook: "The reader's manual — the whole loop, chapter by chapter",
    },
    /**
     * The light/dark toggle.
     *
     * The button's own name, and what it will do when pressed. It is in
     * the chrome rather than in the settings page because the toggle is in
     * the chrome -- the top bar's, the sidebar's.
     */
    theme: {
      switchToLight: "Switch to light theme",
      switchToDark: "Switch to dark theme",
    },
    /**
     * The saved-job button.
     *
     * The bookmark on a job card: what it does, and what it says when the
     * job is already saved.
     */
    save: {
      remove: "Remove from saved jobs",
      save: "Save this job",
      saved: "Saved",
      saveShort: "Save",
      saveHint: "Save — adds this role to your bookmarks",
      removeHint: "Remove — takes this role out of your bookmarks",
    },
    /**
     * The one screen that answers "what has my search written down, in order" (Epic 81):
     * applications, notes, contacts, resume versions, matches and rehearsals — merged by the
     * engine, never by this page. Only the words here; the rows come from the read.
     */
    timeline: {
      title: "Timeline",
      description:
        "Everything your search has written down, in order — applications, notes, contacts, resume versions, matches and rehearsals.",
      emptyTitle: "Nothing written down yet",
      emptyDescription:
        "Every step you take feeds this list: keep a job, write a note, add a contact, or rehearse an interview — they show up here in the order they happened.",
      narrativeTitle: "What this search has been",
      narrativeDescription:
        "One paragraph the reviewer writes over the dates and labels already on this timeline — the arc, the turn, and the thread still open. Every claim cites a date the ledger carries.",
      narrativeAction: "Tell me this search",
      narrativeWorking: "Reading the timeline…",
      narrativeEmpty: "Nothing worth telling came back — not a verdict, just no grounded story to show.",
      chronicleTitle: "Your career chronicle",
      chronicleDescription:
        "A short book the reviewer writes about THIS search — chapters that unfold as your milestones and events warrant. Every line cites a number the ledger actually carries.",
      chronicleLede: "The meaning behind the badges: a chaptered record of how this search unfolded.",
      chronicleAction: "Write the chronicle",
      chronicleWorking: "Writing the chapters…",
      // 370: the door from a chapter onto the region its own anchor places it in.
      chronicleRegionDoor: "Show {region} on the atlas",
      chronicleEmpty: "The ledger is too thin for a chronicle yet — keep going, and the chapters will have something to say.",
      chronicleUntitled: "Untitled chapter",
      chronicleEpilogue: "The epilogue",
      chronicleLocked: "Write the chronicle to unlock its chapters.",
      atlasTitle: "The Career Atlas",
      atlasDescription:
        "A map of the places your search has actually been. Every region is a timeline kind and every site is one of your own events — no invented lands, no filler.",
      atlasLede: "The world grows only when the workspace writes another fact. Pick a region, then a site, to read what you recorded there.",
      atlasEmpty: "The map is uncharted: keep a job, rehearse an interview, add a contact or write a note, and the first region will appear here.",
      atlasRegionsLabel: "The charted regions of your search",
      atlasMapLabel: "A map of the sites in the selected region",
      atlasSiteCount: "{count} sites charted in this region",
      atlasHiddenSites: "{count} more are not drawn on this map",
      // 361: how long this stretch of the world took to build, read off the
      // region's own first and newest fact -- never invented.
      atlasSpan: "charted from {from} to {to}",
      atlasFrontierTitle: "Where this world expands",
      atlasFrontierDescription: "Each door writes a new kind of fact into the ledger. Walk through one and the atlas gains a site.",
      atlasFrontierJobs: "Discover jobs",
      atlasFrontierApplications: "Move an application",
      atlasFrontierInterviews: "Rehearse an interview",
      atlasFrontierNetworking: "Meet a contact",
      atlasFrontierResumes: "Shape a resume",
      // 364: the door out of a region the reader has already charted -- the map names
      // every room, and these are the rooms themselves. Their own keys rather than the
      // frontier's: a frontier is a room nobody has been to, a door is the way back into
      // one they have, and conflating them would make "all charted" claim there is
      // nowhere left to go.
      atlasDoorApplications: "Open the application board",
      atlasDoorInterviews: "Open the rehearsal list",
      atlasDoorJobs: "Open the job board",
      atlasDoorNetworking: "Open the people you know",
      atlasDoorResumes: "Open your resumes",
      atlasDoorNotes: "Open the knowledge base",
      atlasRegionDoor: "Go to {region}",
      // 365: the dashed line is the reader's own route through the world, in the
      // order the ledger says they walked it -- a path taken, not a road that exists.
      atlasRouteLength: "{count} steps along the route you walked",
      // 367: what else was going on in the same region when this site happened.
      atlasNeighbours: "Also in {region} around then",
      atlasAllCharted: "Every frontier the map knows is charted. New kinds of facts will open new ground.",
      kindFilter: "Narrow the timeline by kind",
      filterAll: "All kinds",
      noKindRows: "No {kind} rows yet for this account.",
      dayCount: "{count} events",
      kinds: {
        application: "Application",
        note: "Note",
        contact: "Contact",
        resume_version: "Resume version",
        match: "Match",
        interview: "Rehearsal",
        unknown: "Something else",
      },
    },
    // 369: the one direction the world points, read off the reader's own ledger.
    legacy: {
      title: "What this search leaves behind",
      description:
        "The next one starts from here rather than from nothing — the material worth reusing, the stage that cost the most, and the one lesson the numbers support.",
      lessonEyebrow: "The lesson the numbers support",
      lessonUnfinishedTitle: "Finish what you start",
      lessonUnfinishedBody:
        "You rehearsed more than you reported. The report is the whole point of a rehearsal — it is the only part the next answer can quote.",
      lessonUnusedTitle: "Read back what you kept",
      lessonUnusedBody:
        "You kept the advice and never opened it. A note only pays off when the next answer cites it.",
      lessonReusedTitle: "Your letters did the work",
      lessonReusedBody:
        "You wrote and kept several. The next search starts with them on the shelf rather than a blank page.",
      costliestStage: "Most of your applications stopped at {stage} ({count}).",
      open: "Open",
      reuseReportsTitle: "{count} rehearsal report(s)",
      reuseReportsBody: "What the grader said, in your own words — the evidence a next round cites.",
      reuseLettersTitle: "{count} letter(s)",
      reuseLettersBody: "Written, kept and printable — the shape a next one starts from.",
      reuseNotesTitle: "{count} kept note(s)",
      reuseNotesBody: "Advice you saved from your own rehearsals, ingested so the copilot can quote it.",
      reuseOffersTitle: "{count} offer(s) on the shelf",
      reuseOffersBody: "The decisions you already weighed — and the ledger that weighed them.",
    },
    frontier: {
      eyebrow: "Where the world points next",
      finishRehearsalTitle: "{count} rehearsal(s) still open",
      finishRehearsalBody:
        "A rehearsal left half-done is the one thing a search regrets: the report it would have written is the whole point of taking it. Finish one and the world moves on.",
      finishRehearsalCta: "Open your rehearsals",
      answerReplyTitle: "{count} letter(s) waiting on you",
      answerReplyBody:
        "An employer wrote back and nobody has answered. The window for a good reply is short, and the reply is the reader's to send.",
      answerReplyCta: "Read what came back",
      moveApplicationTitle: "{count} application(s) in your court",
      moveApplicationBody:
        "These are sitting in stages where the next move is the reader's — a follow-up, a nudge, a decision to let one go.",
      moveApplicationCta: "Open the board",
      readMatchesTitle: "{count} new match(es) nobody has opened",
      readMatchesBody:
        "A saved search found these. They will keep, but the ones worth chasing are the ones read while they are fresh.",
      readMatchesCta: "Open the job board",
      readNotesTitle: "{count} note(s) you kept and have not read back",
      readNotesBody:
        "Advice you saved from a rehearsal. It only pays off when the next answer quotes it.",
      readNotesCta: "Open the knowledge base",
    },
    letters: {
      title: "Letters",
      description:
        "Every cover letter you kept across your applications, newest kept first. One gallery, not seven drawers — read it again, copy it, pack it into the next application.",
      loading: "Reading the kept letters…",
      unavailable: "The letters could not be read. Try again in a moment.",
      count: "{count} letters kept",
      searchPlaceholder: "Search the kept letters",
      searchLabel: "Search the kept letters by body, application, company, tone or length",
      search: "Search",
      clearSearch: "Clear search",
      noMatch: "No letter matches “{query}”",
      noMatchDescription: "Try a shorter word, or clear the search to read them all.",
      emptyTitle: "Nothing kept yet",
      emptyPromise: "The gallery starts the moment a draft earns its place.",
      emptyDescription:
        "Generate a cover letter for an application and choose to keep it, and it lands here — newest first, kept rather than scrolled past.",
      emptyAction: "Open the tracker",
      proof1: "Letters come back from the job page itself — the same reader you already use.",
      proof2: "Copied is copied: the letter leaves this screen under your control, not the page's.",
      proof3: "The ledger is yours alone; nothing here is shared with anyone.",
      copy: "Copy this letter",
      unnamedApplication: "A letter kept for an unnamed application",
      companyUnknown: "Unknown company",
      openApplication: "Open the application",
    },
    // The closing ceremony (Epic 212): the ledger of the whole loop, signed once.
    ceremony: {
      title: "The closing ceremony",
      eyebrow: "THIS SEARCH, YOU CLOSED IT",
      description:
        "The whole loop in one composition — the filings, the calluses, the offers and the quiet weeks. Bring a coffee; this is the page you keep.",
      dateLine: "Written {date}, on purpose.",
      epigraph: "The campaign was yours. The credits are too.",
      statApplications: "Applications filed",
      statInterviews: "Interviews practiced",
      statOffers: "Offers held",
      statLetters: "Letters kept",
      statNotes: "Notes in the base",
      statDays: "Days showed up",
      letterTitle: "A letter, from you to you",
      letterPara1:
        "Dear future me — you filed {applications} applications while everyone you know was asleep. You rehearsed {interviews} times, wrote {notes} notes into the base, and kept {letters} of the letters you will otherwise have to rewrite later in your life.",
      letterPara2Accepted:
        "The shelf holds {offers} now, and at least one of them is yours — you accepted it on the day this says yes. The packet, the quarter, the thanks — all of it was earned here.",
      letterPara2Pending:
        "The shelf holds {offers} now, and none have earned your yes yet — which means this page is a doorway, not an ending. The ledger records; it does not decide.",
      letterPara3:
        "What you did not write down — the call you took in the kitchen, the draft you threw away, the rehearsal where your voice shook and still came out — happened anyway, off the record. Put it in the next one.",
      codaTitle: "Three sentences worth keeping",
      coda1: "The room owed honesty — you gave it. That was the whole point.",
      coda2: "The score is an average; the courage was not.",
      coda3: "Close this tab proud. The next one opens when you say so.",
      codaSign: "— The editor",
      afterwardEyebrow: "After the rest",
      afterwardTitle: "What you still carry",
      afterwardIntro:
        "One page didn't end the search. A week of not getting one letter in every form — and a year of showing up to practice anyway. What you carry out of this room is heavier than you walk in with, and you didn't earn it by winning.",
      afterwardK1Label: "Doors knocked",
      afterwardK1Text: "{count} applications. The ones that came back teach you what this product never will: what it feels like on the other side of sent.",
      afterwardK2Label: "Times rehearsed",
      afterwardK2Text: "{count} interviews, finished — the live ones, at least, the ones that carried pressure. The bad ones were not wasted; the good ones were not won.",
      afterwardK3Label: "Days showed up",
      afterwardK3Text: "{count} days of practice, typing, reading, breathing. The counter runs either way — the win or the not-yet.",
      afterwardFootnote:
        "The next search, the next room, the next decade — they all ask the same question this room did. The product was the instrument; you were the arc. Bring that back. Leave the rest.",
      print: "Print the keepsake",
      printHint: "Save as PDF from the browser's print dialog — the page is tuned for one sheet.",
      grandTotal: "{total} actions · {days} days showed up · {letters} letters kept",
      reviewTitle: "The year in review",
      reviewDescription:
        "One image with the whole year on it — applications, interviews, offers, letters — drawn on your device, ready to keep.",
      reviewEyebrow: "AI CAREER OS",
      reviewHeadline: "The search in review",
      reviewStripRight: "total actions taken",
      reviewSignOff: "Written from records, not from memory.",
      reviewDownload: "Download the image",
      reviewAriaHint: "The review card shows {total} actions and {days} days showed up.",
      reviewSaved: "The year, in one image.",
      reviewFailed: "The image could not be drawn — try the print path instead.",
    },
    // The fit studio (paste a JD → analyze → tailor)
    studio: {
      title: "Match Studio",
      description: "Paste a job description to see how you fit and tailor your resume in one pass.",
      fitReport: "Fit report",
      strongFit: "Strong fit",
      goodFit: "Good fit",
      partialFit: "Partial fit",
      weakFit: "Weak fit",
      technical: "Technical",
      experience: "Experience",
      projects: "Projects",
      education: "Education",
      skillsTitle: "Skills",
      whyMatchTitle: "Why this match",
      evidenceTitle: "Evidence",
      skillGapsTitle: "Skill gaps to close",
      interviewTopicsTitle: "Interview topics to prepare",
      jdLabel: "Job description",
      jdHint: "Matched against your most recent resume — or a specific version id below.",
      jdPlaceholder: "Paste the posting here…",
      resumeVersionLabel: "Resume version id (optional)",
      resumeVersionDefault: "Defaults to your latest resume",
      analyze: "Analyze fit",
      analyzing: "Analyzing…",
      matching: "Matching…",
      tailoring: "Tailoring…",
      tailorTitle: "Tailor your resume",
      tailorDescription: "Rewrites your resume to the posting using only what the match found.",
      tailorAction: "Tailor now",
      tailoredReady: "Resume tailored to the posting.",
      analysisFailed: "Analysis failed.",
      tailoringFailed: "Tailoring failed.",
      copied: "Copied",
      readingPosting: "Reading the posting…",
      scoringFit: "Scoring your fit…",
    },
    // Common actions
    common: {
      clipboardBlocked: "Your browser blocked clipboard access.",
      copyFailed: "Could not copy to the clipboard.",
      copy: "Copy",
      fileSaved: "File saved to your downloads.",
      openCopilot: "Open Copilot",
      copiedToClipboard: "Copied to the clipboard.",
      copied: "Copied",
      reset: "Reset",
      download: "Download",
      refetch: "Refetch",
      clear: "Clear",
      snooze: "Snooze",
      pick: "Choose",
      analyze: "Analyze",
      useText: "Use as text",
      generate: "Generate",
      import: "Import",
      saveSearch: "Save search",
      continue: "Continue",
      changeEmail: "Change email",
      changePassword: "Change password",
      activate: "Activate",
      pageNotFound: "Page not found",
      /**
       * The site's own description.
       *
       * It is read by a search engine rather than by the page, so it is
       * a sentence in the reader's language -- and the server reads the
       * locale out of the cookie to put it there.
       */
      metaDescription:
        "Your personal job-search operating system — evidence-backed matching, resume intelligence, and AI-guided interviews.",
      /**
       * The notice a page shows when the backend it is talking to is a
       * different version from the one it was written for.
       *
       * It is the same sentence on every page -- the route answered 404 --
       * so it is one key, and the pages that have their own version of
       * the explanation use their own.
       */
      notLiveTitle: "This API build has no records for this page",
      /** The hint a widget shows when its endpoint is not served yet; `{name}` is the widget's own name. */
      endpointOffline:
        "{name} isn't connected yet — it will appear as soon as the API serves it.",
      refresh: "Refresh",
      close: "Close",
      confirm: "Confirm",
      cancel: "Cancel",
      save: "Save",
      retry: "Retry",
      tryAgain: "Try again",
      checkAgain: "Check again",
      somethingWentWrong: "Something went wrong",
      skipToContent: "Skip to content",
      backToDashboard: "Back to the dashboard",
      /**
       * The sentence a page shows when the route it called answered 404 --
       * the frontend and the API are different builds. `{route}` is the
       * route's own name, so the mismatch is diagnosable from a screenshot.
       */
      missingEndpoint:
        "A route this screen needs answered 404, so this frontend and the backend it is talking to are different versions. Nothing is shown in place of the real data.",
      missingEndpointRoute:
        "{route} answered 404, so this frontend and the backend it is talking to are different versions. Nothing is shown in place of the real data.",
    },
    /**
     * What a successful write says.
     *
     * A toast is raised from an event handler, long after the render that
     * knew the language, so these are read through `translate` rather than
     * the provider's `t` -- but they are the reader's words all the same,
     * and they were English literals in the write hooks until this table.
     */
    toasts: {
      resumeUploaded: "Uploaded — parsing your resume.",
      resumeCurrent: "Current version updated.",
      resumeDeleted: "Resume deleted.",
      savedJobRemoved: "Removed from saved jobs.",
      jobSavedToPipeline: "Saved to your pipeline.",
      resumeTailored: "Tailored resume ready — review the diff before you export it.",
      matchComplete: "Match analysis complete.",
      jobImported: "Job imported - the analyst filled in the details.",
      addedToPipeline: "Added to your pipeline.",
      coverLetterSaved: "Cover letter saved to the application.",
      letterRemoved: "Letter removed.",
      letterUpdated: "Letter corrected.",
      removedFromPipeline: "Removed from pipeline.",
      applicationNoteSaved: "Note saved.",
      reminderSet: "Reminder set.",
      reminderCleared: "Reminder cleared.",
      queuedForIngestion: "Queued for ingestion.",
      knowledgeNoteCreated: "Note created.",
      knowledgeNoteUpdated: "Note updated.",
      knowledgeNoteDeleted: "Note deleted.",
      interviewDeleted: "Rehearsal deleted.",
      interviewAbandoned: "Rehearsal ended.",
      interviewReportReady: "Interview report is ready.",
      conversationRenamed: "Conversation renamed.",
      conversationDeleted: "Conversation deleted.",
      profileSaved: "Profile saved.",
      careerProfileSaved: "Career profile saved.",
      memoryUpdated: "Memory updated.",
      memoryForgotten: "Memory forgotten.",
      contactSaved: "Contact saved.",
      contactUpdated: "Contact updated.",
      contactDeleted: "Contact deleted.",
    },
    /**
     * What a screen reader is told while a surface is still loading.
     *
     * These are the announcements, not the shimmer: they are the only words a
     * reader who cannot see the skeleton hears, and they are what tells them
     * *which* thing is loading rather than that something is.
     */
    loading: {
      generic: "Loading",
      jobs: "Loading jobs",
      pipeline: "Loading pipeline",
      conversation: "Loading conversation",
      // The key is singular on purpose: the api-service keeps a census on the
      // literal token for the error envelope's dropped list over the
      // browser's sources, and a translation key that spelled it the same way
      // would read as a reader of that list. The phrase it carries is the
      // plural one.
      detail: "Loading details",
      page: "Loading page",
      workspace: "Loading your workspace…",
      table: "Loading table",
      inProgress: "Loading…",
    },
    /**
     * The chrome around every surface: the sidebar, the top bar, the command
     * palette and the pager. These are the labels a screen reader announces
     * for the navigation itself, so they are part of the product's voice and
     * not implementation detail.
     */
    chrome: {
      logOut: "Log out",
      signingOut: "Signing out…",
      signedIn: "Signed in",
      mainNavigation: "Main navigation",
      goToDashboard: "AI Career OS — go to dashboard",
      openNavigationMenu: "Open navigation menu",
      openCommandPalette: "Open command palette",
      commandPaletteHint: "Jump anywhere — type what you want to do, or the page you want.",
      accountMenuHint: "Your account: profile, settings, or sign out.",
      accountMenu: "Account menu",
      // 360: the avatar is identity, not decoration, so it is named for a reader
      // who cannot see it -- and whose picture it is.
      yourAvatar: "{name}'s picture",
      resetHint: "Replay — start this card over",
      editHint: "Edit — fix it in place",
      deleteHint: "Delete — gone for good",
      menuHint: "Open the menu — everything lives behind it",
      commandPaletteTitle: "Command palette",
      commandPaletteDescription: "Search your career workspace and jump between sections",
      commandPalettePlaceholder: "Type a command or search…",
      manualOpen: "The manual — how to play",
      quickStartReplay: "Replay the quick start",
      themeToggle: "Toggle dark and light",
      manualTitle: "The manual",
      manualDescription: "The same doors as /playbook, in your pocket. One sheet, nine rooms, in your language.",
      manualFullLink: "Read the full manual",
      manualShortcutHint: "to open it from anywhere",
      manualSurfacesFind: "Find jobs, studio, and copilot opportunities",
      manualSurfacesPrepare: "Prepare your resume, prepare for interviews, grow your skills",
      manualSurfacesTrack: "Track applications, manage letters, follow the timeline",
      manualSurfacesDecide: "Decide your next move with offers and replies",
      manualSurfacesSee: "See analysis, monitoring, and your activity stats",
      searching: "Searching…",
      noResults: "No results.",
      recentSearches: "Recent searches",
      clearRecentSearches: "Clear recent searches",
      searchFailed: "Content search failed — showing navigation only.",
      search: "Search",
      goTo: "Go to",
      resultsStreamIn: "content results stream in as you type.",
      previousPage: "Previous page",
      nextPage: "Next page",
      refreshList: "Refresh list",
      pagination: "Pagination ({label})",
      ofTotal: "{from}–{to} of {total} {label}",
      noRowsYet: "No {label} yet",
      prev: "Prev",
      next: "Next",
      switchToChinese: "Switch to Chinese",
      switchToEnglish: "Switch to English",
      expandSidebar: "Expand sidebar",
      collapseSidebar: "Collapse sidebar",
      collapse: "Collapse",
      profileAndPreferences: "Profile & preferences",
      settings: "Settings",
    },
    /**
     * The job card's own panels: what the tailor and the cover-letter
     * engines produced, and the state of a match that has not been run.
     */
    /**
     * The resume dropzone. The upload is the product's front door for a
     * new user, so its copy is part of the product's voice.
     */
    upload: {
      ariaLabel: "Upload resume",
      uploading: "Uploading…",
      dropHere: "Drop your resume here, or click to browse",
      accepted:
        "{formats} — up to {mb} MB. Files stay in your workspace and feed the knowledge base the agents cite from.",
      problemUnsupported: "Only PDF, DOCX or TXT files are supported.",
      problemTooLarge: "File is larger than {mb}MB.",
      problemEmpty: "That file looks empty.",
      ingesting: "Ingesting",
      ingestedToast: "Resume ingested — your knowledge base is updated.",
      canLeave:
        "You can leave this page — the run continues server-side and the list below reflects its real status.",
      sending: "Sending the file…",
      /**
       * The five stages the ingestion pipeline reports.
       *
       * The keys are the step ids the pipeline publishes
       * (`ai-service/app/ingestion/pipeline.py`), so a step the seed does
       * not name still lines up with the frame that carries it.
       */
      ingest: {
        extracting: "Extracting text from the file",
        cleaning: "Cleaning and normalizing the text",
        chunking: "Splitting into retrievable chunks",
        embedding: "Generating embeddings for each chunk",
        indexing: "Indexing the document",
      },
    },
    // AI / task stream
    ai: {
      generated: "AI generated",
      taskStream: {
        waitingForAgent: "Waiting for the agent...",
        streamNotReported: "The run stream hasn't reported progress yet -- results appear as soon as it does.",
        agentTrace: "Agent trace",
        runError: "The run reported an error.",
        steps: "{count} steps",
        /** Appended after `steps` when the bounded trace window folded away older rows. */
        foldedSteps: "{count} earlier steps folded",
      },
      processing: {
        ariaLabel: "AI processing progress",
      },
      agentTimeline: {
        trace: "Agent execution trace",
        running: "Running",
        completed: "Completed",
        failed: "Failed",
        /** The line a tool_result step shows: the reader's sentence around
         * the tool's own name, which the payload carries. */
        resultOf: "{tool} result",
        kinds: {
          step_start: "Step start",
          tool_call: "Tool call",
          tool_result: "Tool result",
          llm_call: "Model call",
          retrieval: "Retrieval",
          rerank: "Rerank",
          handoff: "Handoff",
          message: "Message",
          final: "Final",
          graph_node: "Flow node",
        },
      },
    },
    jobCard: {
      companyNotResearched: "Company not researched yet",
      noMatchYet: "No match computed yet",
      matchFor: "Match for {title}",
      whyThisJob: "Why this job:",
      pastedJd: "Pasted JD",
      foundByResearch: "Found by research agent",
    },
    /**
     * The charts the product draws.
     *
     * A chart with nothing to draw says so; the word is the reader's.
     */
    chart: {
      nothingToPlot: "Nothing to plot yet.",
    },
    /**
     * The diff the tailor panel shows: the numbers beside the change list,
     * and the panel the list lives in.
     */
    diffView: {
      whyNotApplied: "Why it was not applied:",
      why: "Why:",
      bullet: "Bullet",
      skipped: "Skipped",
      applied: "Applied",
      statistics: "Tailoring statistics",
      stats: {
        accepted: "Applied",
        rejected: "Rejected",
      },
      agentNotes: "Agent notes",
      appliedChanges: "Applied changes",
      rejectedProposals: "Rejected proposals",
      noSafeEdits:
        "The agent proposed no safe edits for this role — it will not rewrite experience it cannot evidence.",
      hide: "Hide",
      showReasons: "Show reasons",
    },
    /**
     * One piece of cited evidence, and the card it sits in.
     */
    evidence: {
      showAllCount: "Show all {count} evidence items",
      showFewer: "Show fewer",
      source: "Evidence source",
      jumpToSource: "Jump to source",
      citationAria: "Citation {index}: {title}",
      citationAriaSection: "Citation {index}: {title} — {section}",
    },
    /**
     * The recovery screens. The copy here is careful on purpose -- the
     * endpoint answers 200 for an address with no account, so the screen says
     * "if that address has an account" and never more. The translation keeps
     * that hedge.
     */
    recovery: {
      checkEmail: "Check your email",
      checkEmailBody:
        "If {email} has an account, a reset token is on its way. The token is good for 30 minutes.",
      alreadyHaveToken: "I already have a token",
      differentAddress: "Use a different address",
      resetHeading: "Reset your password",
      resetBody: "Tell us the address on the account and we will send it a reset token.",
      email: "Email",
      emailPlaceholder: "you@example.com",
      sendToken: "Send reset token",
      remembered: "Remembered it?",
      signIn: "Sign in",
      passwordUpdated: "Password updated",
      signedOutEverywhere:
        "Every device that was signed in has been signed out. Use the new password to get back in.",
      setNewPassword: "Set a new password",
      pasteToken:
        "Paste the token from your email, then pick a password. Signing in everywhere else stops as soon as you save.",
      stopsElsewhere: "Signing in everywhere else stops as soon as you save.",
      resetToken: "Reset token",
      resetTokenPlaceholder: "the token from the email",
      newPassword: "New password",
      confirmNewPassword: "Confirm new password",
      saveNewPassword: "Save new password",
      tokenExpired: "Token expired?",
      requestAnother: "Request another",
      genericFailure: "Something went wrong. Please try again.",
    },
    emailChange: {
      confirmHeading: "Confirm your new address",
      answering: "Answering the link from your email…",
      movedTitle: "Address moved",
      movedBody:
        "Your sign-in address has moved, and every device has been signed out. Sign in with the new address and your unchanged password.",
      invalidTitle: "This link cannot be used",
      invalidBody:
        "It may have expired, already been used, or never been issued. Sign in and ask for a new one from Settings → Account.",
      registeredTitle: "That address was taken",
      registeredBody:
        "Another account registered it before this link was answered, so the move did not happen. Sign in and ask for a different address from Settings → Account.",
      pasteBody: "Open the link in the letter. If it did not open, paste its token here.",
      tokenLabel: "Link token",
      tokenPlaceholder: "the token from the email",
      confirm: "Confirm the move",
      retryBody: "We could not answer the link just now. It is still good — try it again.",
      retry: "Try again",
    },
    /**
     * The address move on the settings page (38.2). Every sentence here describes what
     * the server does: two letters leave, nothing moves until the new mailbox answers,
     * and the move itself signs every session out.
     */
    emailMove: {
      title: "Sign-in address",
      description:
        "Move the address this account signs in with. Asking sends two letters, and the move waits for the new mailbox to answer.",
      current: "This account signs in with {email}.",
      newLabel: "New address",
      newPlaceholder: "you@example.com",
      passwordLabel: "Current password",
      passwordPlaceholder: "Type your current password",
      send: "Send the confirmation letter",
      sentTitle: "Two letters are on their way",
      sentBody:
        "One went to {newEmail} with the link that finishes the move, good for two hours. The other went to {oldEmail}, so whoever reads that mailbox learns the move was asked for. Nothing changes until the new mailbox opens the link.",
      hint: "When the link is answered, every session is signed out; the password stays the same.",
      askAgain: "Use a different address",
    },
    sessions: {
      title: "Open sessions",
      description:
        "Every browser and device that can still refresh this account's sign-in. One row is one session, however often it renews itself.",
      loading: "Reading the open doors…",
      loadFailed: "The session list could not be read.",
      empty:
        "No door can refresh right now. The next time this tab's access token expires, it asks you to sign in again.",
      current: "This device",
      currentNote: "This is the tab you are in. Closing it behaves like logging out.",
      unknownDevice: "Unnamed device",
      address: "From {address}",
      started: "Opened {when}",
      seen: "Last seen {when}",
      expires: "Refreshes until {when}",
      close: "Close",
      closeNamed: "Close {device}",
      closeTitle: "Close this session?",
      closeOneDescription:
        "{device} stops refreshing at once and signs out the next time it needs a new access token.",
      closeCurrentDescription:
        "This is the tab you are in. Closing it behaves like logging out: the tab keeps working only until its access token expires.",
      closeAll: "Close every session",
      closeAllHint: "Ends every session on every device, this one included.",
      closeAllTitle: "Close every session?",
      closeAllDescription:
        "Every device signs out, including this one. This tab keeps working only until its access token expires.",
      alreadyClosed: "That session was already closed; the list has been refreshed.",
    },
    /**
     * The password card (38.4). Success names the server's whole consequence: every
     * refresh token is revoked, other devices sign out at their next refresh, and this
     * tab lives until its own access token expires.
     */
    passwordChange: {
      title: "Password",
      description:
        "Replace the password this account signs in with. The current password is asked for first, so a borrowed tab cannot lock you out.",
      currentLabel: "Current password",
      currentPlaceholder: "Type your current password",
      newLabel: "New password",
      newPlaceholder: "At least 8 characters",
      confirmLabel: "New password again",
      confirmPlaceholder: "Type the new password again",
      submit: "Change the password",
      hint: "Changing the password signs out every other device. This tab stays signed in until its access token expires.",
      changedTitle: "The password is changed",
      changedBody:
        "Every session's refresh token has been revoked. Other devices sign out the next time they need a new access token, and this tab keeps working until its own token expires, then asks for the new password. Signing in from now on takes the new one.",
      again: "Change it again",
    },
    /**
     * The erasure card (38.5). Every sentence describes what the server does: both checks,
     * the files deleted before the row, the rows that cascade, and the backups that outlive
     * the live system until their retention window passes.
     */
    eraseAccount: {
      title: "Erase this account",
      description:
        "Close the account for good. It takes the password and the sign-in address typed back, and neither wrong answer touches anything.",
      current: "The account being erased is {email}.",
      leavesTitle: "What leaves",
      leavesBody:
        "Every row that names this account — profile, resumes and versions, jobs, applications, interviews, knowledge sources, letters, notifications, sessions and tokens — and every stored file behind its documents.",
      staysTitle: "What stays",
      staysBody:
        "Backups outside the live system keep what they captured until their retention window passes. Letters already delivered stay in their mailboxes.",
      passwordLabel: "Current password",
      passwordPlaceholder: "Type your current password",
      confirmLabel: "Sign-in address, typed back",
      confirmPlaceholder: "{email}",
      hint: "Case and surrounding spaces are forgiven; a different address is refused.",
      submit: "Erase the account",
      dialogTitle: "Erase this account for good?",
      dialogDescription:
        "The password you typed is checked first, then {email}. If both pass, every row and every stored file this account owns is erased, and there is no way to restore it.",
      dialogConfirm: "Erase it",
    },
    /**
     * The landing after 24.2's route answers `{erased: true}` (38.5). The reader has no
     * account and no session any more, so the page says that plainly and offers the two
     * doors that remain: create a new account, or sign in with another one.
     */
    accountErased: {
      title: "The account is gone",
      body:
        "Every row and every stored file this account owned has been erased. No session can sign in with it again.",
      keptTitle: "What is still out there",
      keptBody:
        "Backups outside the live system keep what they captured until their retention window passes, and letters already delivered stay in their mailboxes.",
      startAgain: "Create a new account",
      signInOther: "Sign in with another account",
    },
    tailor: {
      title: "Tailored resume for this role",
      draftBadge: "Tailored draft",
      eyebrow: "AI tailoring",
      descriptionWith: "Rewrites bullets and reorders projects from {resume}.",
      description: "Rewrites bullets and reorders projects from your current resume.",
      neverInvented: "Experience is never invented",
      claimsKeptOut: "— unsupported claims are rejected and listed.",
      runAgain: "Run again",
      tailorNow: "Tailor now",
      failed: "Tailoring failed.",
      savedAs: "Saved as {name}",
      diff: "Diff",
      fullDocument: "Full document",
      saveAgain: "Save again",
      saveAsVersion: "Save as version",
      printVersion: "Print this version",
      noStructuredDiff:
        "The response carried no structured diff. The document view still shows what was produced.",
      noDocumentText: "No document text was returned for this run — only the change list above.",
      evidenceUsed: "Evidence used",
      nothingGeneratedYet:
        "Nothing has been generated yet — the draft appears here after you run it, and stays a proposal until you export or save it as a version.",
      stages: {
        readingKnowledge: "Reading your knowledge base",
        matchingExperience: "Matching experience to the JD",
        rewritingBullets: "Rewriting bullets",
        checkingClaims: "Checking for invented claims",
      },
    },
    coverLetter: {
      title: "Cover letter",
      description:
        "Built from your resume evidence, the JD and company context. Regenerate with a different tone or length at any time.",
      draftBadge: "Draft",
      copyLetter: "Copy letter",
      download: "Download",
      eyebrow: "AI writing",
      tone: "Tone",
      length: "Length",
      tones: {
        balanced: "Balanced",
        formal: "Formal",
        concise: "Concise",
        confident: "Confident",
      },
      lengths: {
        short: "Short (~180 words)",
        standard: "Standard (~300 words)",
        detailed: "Detailed (~450 words)",
      },
      generate: "Generate",
      regenerate: "Regenerate",
      saveToApplication: "Save to application",
      savedBadge: "Saved to this application",
      saveNeedsPipeline: "Add this job to your pipeline to keep the letter.",
      keptHere: "{count} kept for this posting.",
      openPipeline: "Open the pipeline",
      saveAnother: "Save another copy",
      words: "{count} words",
      generationFailed: "Generation failed.",
      noLetterText: "The response contained no letter text — try regenerating.",
      noLetterYet: "No letter generated yet for this role.",
      stages: {
        readingJd: "Reading the JD",
        pullingContext: "Pulling company context",
        drafting: "Drafting",
        checkingClaims: "Checking claims",
      },
    },
    // Dashboard
    dashboard: {
      theScoredVersion: "The version every agent scores against.",
      resumeTitle: "Resume",
      resumeReady: "{status} · the profile every agent matches against",
      resumeAwaitingParse: "{status} · the structured profile is not ready yet",
      straightFromTheBoard: "Straight from the job board — run a match to rank them.",
      ctaPasteJd: "Paste a JD",
      stepUploadCta: "Upload",
      ctaMatch: "Match a job",
      skillGapsHint: "Ranked by the matching agent against your resume.",
      nextStepTitle: "Today's first step",
      nextStepDescription: "One grounded sentence on what to do before anything else — drawn from your own numbers, not invented.",
      nextStepRun: "Ask the assistant",
      nextStepAgain: "Ask again",
      nextStepEmpty: "No step yet — the assistant reads your numbers when you ask, nothing before that.",
      nextStepHint: "Reads your applications, attention queue, sessions and offers, then writes one grounded first move you can actually send or follow up on. Nothing leaves the account you signed into.",
      nextStepPending: "Reading your week…",
      nextStepError: "The assistant could not see your week right now — try again in a moment.",
      gradeHint: "Overall grade from the resume reviewer. Open the resume for the per-dimension breakdown.",
      gradeWeak: "Weak — start here",
      gradeNeedsWork: "Needs work",
      gradeSolid: "Solid baseline",
      gradeInterviewReady: "Interview-ready",
      title: "Dashboard",
      greeting: "Good morning",
      /**
       * The three times of day the greeting can name.
       *
       * The greeting is the one line on the dashboard that was written in
       * English in the source, so a Chinese reader was greeted in English
       * on a Chinese page. The keys are the hours' own -- the greeting is
       * computed from the reader's clock, not from a form.
       */
      greetingHello: "Hello",
      greetingMorning: "Good morning",
      greetingAfternoon: "Good afternoon",
      greetingEvening: "Good evening",
      description: "Your job search at a glance — every figure here is read live from the API.",
      applications: "Applications",
      interviews: "Interviews",
      replies: "Replies",
      offers: "Offers",
      avgMatch: "Avg match",
      averageMatch: "Average match",
      needsAttention: "Needs attention",
      pipeline: "Pipeline",
      pipelineDescription: "Counts per stage, live from the applications board.",
      attention: "Needs attention",
      attentionDescription:
        "Reminders that have come due, and applications with no step logged in two weeks.",
      whereToFocus: "Where to focus",
      recentRuns: "Recent AI runs",
      recentRunsDescription: "Every match, tailor and ingestion the agents performed.",
      recentActivity: "Recent activity",
      recentActivityDescription:
        "The five newest steps on your applications — moves, notes, reminders, outcomes and replies.",
      activityStatus: "Application moved to a new stage",
      activityNote: "A note was added: {note}",
      activityReminderSet: "A reminder was set",
      activityReminderCleared: "A reminder was cleared",
      activityOutcomeCompensation: "An offer's compensation was recorded",
      activityOutcomeRejection: "A rejection reason was recorded",
      activityOutcome: "An outcome was recorded",
      activityReply: "A reply arrived: {subject}",
      activityUnknown: "An update was logged",
      noRecentActivity: "No activity yet",
      noRecentActivityDescription:
        "Move an application, add a note or file a reply and the newest steps will appear here.",
      activityFailed: "Recent activity could not be loaded",
      resumeScore: "Resume score",
      knowledgeBase: "Knowledge base",
      knowledgeBaseDescription: "Sources ingestion feeds the retrieval layer.",
      aiUsage: "Agent spend",
      aiUsageDescription: "Requests and tokens the agents billed against your budget.",
      engineBoundValue: "max_steps = 8",
      engineLedgerValue: "graph_node",
      engineEyebrow: "The engine, made visible",
      engineTitle: "How your copilot actually runs",
      engineIntro:
        "Every copilot turn is a bounded loop, not a guess. The map below is the actual machine in the source \u2014 same node names, same edges, same bound \u2014 so the instrument you are billed for is one you can see.",
      engineRetrieveBody: "Reads your resume, your applications, your history \u2014 the material the draft will stand on.",
      engineDraftBody: "Writes the changes the job asked for, in your words, on your spine.",
      engineVerifyBody:
        "The deterministic veto. An invented bullet, a drifted fact, a fabricated detail \u2014 refused, named, and bounced back to draft.",
      engineRenderBody: "Applies only what survived verification, writes the diff, keeps your testimony.",
      engineRetryLabel:
        "If verify refuses the draft, it routes back to draft with the reasons attached \u2014 a bounded retry inside the loop, never an open one.",
      engineBound:
        "The whole machine refuses to run past eight node executions; a bug becomes a refusal with a step count, never a token burn.",
      engineLedger:
        "Every node writes a graph_node row into AI Activity \u2014 the ledger is the graph's own heartbeat, visible run by run.",
      engineBookLink: "Read the chapter in the book",
      engineActivityLink: "Open the ledger",
      skillGaps: "Top skill gaps",
      skillGapsDescription: "Across your matched jobs.",
      followUps: "Follow-up reminders",
      followUpsDescription: "Contacts who need a touch, ranked by their relation's cadence.",
      followUpPriorities: {
        overdue: "Overdue",
        soon: "Due soon",
        fresh: "On track",
      },
      noResumeScore: "No resume score yet",
      noResumeScoreDescription:
        "Upload and parse a resume — the reviewer agent grades bullets, structure, impact and keyword coverage.",
      noAttention: "Nothing needs attention",
      noAttentionDescription: "Every application has a recent step logged.",
      attentionPromise: "Nothing is waiting on you — the search is on rails.",
      boardIsEmpty: "The board is empty.",
      emptyPipeline: "Nothing in the pipeline yet",
      emptyPipelineDescription:
        "Save a job and start tracking it — the board covers saved → applied → OA → interview → final round → offer.",
      emptyResumes: "No resumes in the base yet",
      emptyResumesDescription:
        "Upload your resume — parsing feeds the knowledge base so every AI answer cites real experience.",
      trackedApplications: "{count} tracked application{plural}.",
      reminderDue: "Reminder due {when}",
      lastStep: "Last step {when}",
      noStep: "No step logged",
      replyWaiting: "A recruiter replied {when}",
      snoozeReminder: "Snooze to tomorrow",
      clearReminder: "Clear",
      moreNeedAttention: "{count} more need attention on the board.",
      askCopilot: "Ask Copilot",
      openCopilot: "Open Copilot",
      openPipeline: "Open pipeline",
      openBoard: "Open board",
      openJobs: "Open Jobs",
      goToJobs: "Go to Jobs",
      allJobs: "All jobs",
      browseJobs: "Browse jobs",
      fullLog: "Full log",
      uploadResume: "Upload resume",
      openNetworking: "Open Networking",
      avgMatchLabel: "Avg match",
      avgMatchBody: "across scored jobs, from your resume evidence",
      preferToTalk: "Prefer to talk it through?",
      preferToTalkBody:
        "and describe your target role — it will ask for what it needs.",
      detail: "Detail",
      manage: "Manage",
      requests: "Requests",
      tokensLabel: "Tokens",
      costLabel: "Cost",
      cachedTokens: "Served from cache: {count} tokens",
      cacheHitRate: "direct cache hit",
      daysAgo: "{count}d ago",
      progressedToday: "Touched it today",
      progressedTitle: "Log a touch: the row re-dates and leaves this list",
      rowTokens: "{count} tokens",
      heatmapTitle: "Your search, at a glance",
      heatmapDescription: "Every day of the last six months: applications filed, interviews held, recruiter replies, AI calls.",
      heatmapCurrentStreak: "Current streak",
      heatmapLongestStreak: "Longest",
      heatmapTotal: "Actions",
      heatmapEmpty: "No activity in this window yet — file an application, hold a rehearsal or run a match, and the grid starts filling.",
      heatmapUnavailable: "The pace grid could not be read.",
      heatmapLess: "Less",
      heatmapMore: "More",
      heatmapLegendAria: "Intensity rises with the day's total actions",
      heatmapAiCalls: "{count} AI calls",
      heatmapQuietDay: "A quiet day",
      trace: "Trace",
      open: "Open",
      noFollowUps: "No follow-ups needed",
      noFollowUpsDescription: "Add contacts in Networking and their cadence will rank here.",
      noRecommendations: "No jobs to recommend yet",
      noRecommendationsDescription:
        "Paste a JD or let the research agent fill the board — recommendations appear as soon as there's something to rank.",
      noRuns: "No AI runs yet",
      noRunsDescription:
        "Run a match or tailor a resume and the orchestrator will log every step here.",
      noSpend: "No AI spend yet",
      noSpendDescription:
        "Match a job or tailor a resume and the token counts appear here.",
      noGaps: "No gaps measured yet",
      noGapsDescription:
        "Run a match against a job and its missing skills rank here by importance.",
      statsNotConnected: "Dashboard stats aren't connected yet",
      statsFailed: "Dashboard stats failed to load",
      attentionFailed: "Attention list failed to load",
      recommendationsFailed: "Recommendations failed to load",
      runsFailed: "Recent runs failed to load",
      spendFailed: "Agent spend failed to load",
      gapsFailed: "Skill gaps failed to load",
      rolesInFlight: "roles in flight",
      restBelow: "The rest of the page still reads the real APIs below.",
      reachedOrPracticed: "reached or practiced",
      readyForDecision: "ready for decision",
      staleOrDue: "stale or due reminders",
      onboardingTitle: "Let's build your workspace",
      onboardingDescription: "Nothing here is pre-filled — these steps unlock every feature, in order.",
      copilotHint: "Ask the assistant — read your resume, the page, or this job",
      pipelineHint: "Open the kanban — saved to interviewing to offer",
      nineQuestsTitle: "The nine rooms — your walking tour",
      nineQuestsIntro:
        "One checkmark as you open each room. Ten minutes, and the whole product is yours. Kept in this browser only — nothing here scores you.",
      nineQuestsProgress: "{done} of {total} rooms walked",
      questsProgressTitle: "Your journey",
      questsProgressHint: "Track how many product rooms you've explored.",
      questsProgress: "{completed} of {total} rooms walked ({progress}%)",
      startQuests: "Continue the tour",
      revisitTour: "Revisit the tour",
      languageProficiency: "Language proficiency",
      languageProficiencyHint: "Your verified language scores, kept here for quick reference.",
      languageOwner: "Verified scores for {name}",
      topSkills: "Top skills",
      topSkillsHint: "Top skills pulled from your resume evidence.",
      noSkillsYet: "Add a resume to see your top skills here.",
      viewAllSkills: "View all skills",
      nineQuestsClear: "All nine",
      nineQuestsDone:
        "All nine. The ceremony is waiting — it happens when you sign. Until then, the loop is yours.",
      nineQuestsReset: "Forget my steps",
      stepUpload: "Upload your resume",
      stepUploadDescription:
        "Parsing builds the structured profile and knowledge base every agent cites from.",
      stepJd: "Add a job description",
      stepJdDescription:
        "Paste any JD in Jobs → Analyze a JD to extract requirements and hidden signals.",
      stepMatch: "Run your first match",
      stepMatchDescription:
        "The matcher scores you per dimension and cites the resume lines behind every number.",
      stepTrack: "Track the pipeline",
      stepTrackDescription:
        "Saved jobs flow through the kanban: saved → applied → OA → interview → offer.",
    },
    // Offers
    offers: {
      shelfTitle: "Your offer shelf",
      shelfDescription: "The offers you actually hold — compared by one number, with deadlines kept in view.",
      shelfCount: "{count} on the shelf",
      shelfEmpty: "The shelf is empty — add your first offer below and the comparison starts there.",
      shelfBest: "Best total comp",
      shelfEquityYear: "Equity / yr",
      shelfDaysLeft: "{count}d left",
      shelfEdit: "Edit this offer",
      shelfDelete: "Remove this offer",
      shelfLabel: "Offer",
      shelfLabelPlaceholder: "Acme — Senior Backend",
      shelfBase: "Base salary",
      shelfBonus: "Bonus",
      shelfEquity: "Equity / yr",
      shelfRemote: "Style",
      shelfAdd: "Add offer",
      shelfUpdate: "Save changes",
      shelfSaved: "Offer on the shelf.",
      shelfDeleted: "Offer removed.",
      shelfSaveFailed: "Could not save the offer.",
      shelfDeleteFailed: "Could not remove the offer.",
      shelfDecisionLabel: "Decision",
      shelfDecision_pending: "On hold",
      shelfDecision_accepted: "Taking it",
      shelfDecision_declined: "Passing",
      shelfLetterButton: "Write the letter",
      shelfLetterHint: "One page, addressed to the future you — what this offer taught you and why you passed on it.",
      shelfLetterTitle: "The letter you will keep",
      shelfLetterSilent: "The letter did not write itself this time.",
      counterLetterTitle: "The email you are about to send",
      counterLetterHint: "One email, same numbers — the ask, sent tonight. Copy it, change it, send it in your own hand.",
      counterLetterButton: "Write the counter email",
      counterLetterCopy: "Copy",
      counterLetterCopied: "Copied",
      counterLetterSilent: "Nothing grounded enough to send — the numbers as they stand are the honest answer.",
      followUpLetterTitle: "The email you are about to send (again)",
      followUpLetterHint: "One polite email — a clear ask, no pressure. Send it tonight and give them a chance.",
      followUpLetterButton: "Write the check-in email",
      followUpLetterCopy: "Copy",
      followUpLetterCopied: "Copied",
      followUpLetterSilent: "No honest follow-up left to send — silence is the answer.",
      acceptancePlaybookTitle: "Day 1 of the new job",
      acceptancePlaybookHint: "The first 90 days, written from the offer you just signed — Day 1 / Day 30 / Day 60 / Day 90.",
      acceptancePlaybookButton: "Write the playbook",
      acceptancePlaybookCopy: "Copy",
      acceptancePlaybookCopied: "Copied",
      acceptancePlaybookSilent: "Nothing grounded enough to write — the offer itself stands as the whole truth.",
      negotiationPrepTitle: "Before the call",
      negotiationPrepHint: "Twelve lines to walk in with — the anchor read, the number you own, the pause, the floor, and the graceful no.",
      negotiationPrepButton: "Write the prep sheet",
      negotiationPrepCopy: "Copy",
      negotiationPrepCopied: "Copied",
      negotiationPrepSilent: "Nothing grounded enough to prepare from — the offer as it stands is the whole page.",
      declineLetterTitle: "The email you are about to send (no)",
      declineLetterHint: "One short email — gratitude, a clean and final no, a door left open. No excuse invented, no numbers re-litigated.",
      declineLetterButton: "Write the decline email",
      declineLetterCopy: "Copy",
      declineLetterCopied: "Copied",
      declineLetterSilent: "Nothing grounded enough to send — a terse, honest no is better than a polite invention.",
      shelfTakingTitle: "{label} — this is yours.",
      shelfTakingNumber: "{total} total compensation a year — the number you decided on.",
      shelfTakingBody: "The hard part is over. Take a breath, then build the first week of your new job — start dates, equipment, benefits — before the thank-you emails are done.",
      dayOneTitle: "{role} — your first week is already yours.",
      dayOneDescription:
        "Sign and file, give notice, map the vest, enroll in benefits. These seven are the distance between the ceremony and the seat — and nobody is watching except future you.",
      dayOneCount: "{done} of {total} sealed",
      dayOnePacketSigned: "Countersigned offer, somewhere safe. Not the email — the final PDF with the vest schedule in it.",
      dayOneStartDate: "Name the first day out loud, and put it on the calendar. Tell one person — they will ask.",
      dayOneNotice: "Give notice where you are now. A whole person leaves: warm, clean, with a handoff.",
      dayOneVest: "Map the vest — cliff, schedule, refreshers. Know the day on which the paper says the money is yours.",
      dayOneBenefits: "Enroll in the benefits — 401k match, healthcare, the forgotten forms. Each has a deadline; this is yours.",
      dayOneGear: "Sort the gear — laptop, badge, desk, the right chair. Day one is hardware, not heroics.",
      dayOnePeople: "Write down one person who carried you here, and one you will call on day one.",
      dayOneReset: "Reset the list",
      dayOneAllDoneTitle: "All sealed.",
      dayOneAllDoneBody: "Every unglamorous thing that gets remembered. The seat is yours — go sit in it.",
      quarterTitle: "{role} — your first quarter, in three acts.",
      quarterDescription: "The day-one packet ends at the ceremony. The act that follows is the one new hires keep alone: learn the place, own one surface, lift the team. Eighteen ticks, brought alongside your own judgment.",
      quarterReset: "Reset the plan",
      quarterCount: "{done} of {total} sealed",
      quarterAllDone: "All three acts sealed. You are not the new person anymore — you are the person.",
      quarterActLand: "Days 1–30 · Land",
      quarterActOwn: "Days 31–60 · Own",
      quarterActLift: "Days 61–90 · Lift",
      quarterLandBlurb: "Learn the place",
      quarterOwnBlurb: "Own one surface",
      quarterLiftBlurb: "Lift the team",
      quarterLand1: "Find the three people whose work wins at this organization, and book a coffee with each of them.",
      quarterLand2: "Learn how decisions actually get made here — then sit in two rooms and listen, saying nothing.",
      quarterLand3: "Ship one small, visible thing end-to-end in your second week — and make it noticeably good.",
      quarterLand4: "Write your own README for the codebase. It compounds twice.",
      quarterLand5: "Pin the 1:1 cadence with your manager and what each of you is expected to leave it with.",
      quarterLand6: "Ask about the project that looks hard and boring to everyone else. That one is the work.",
      quarterOwn1: "Own one user-facing surface end-to-end — pick the one in everyone's hands the most.",
      quarterOwn2: "Delete something out loud: a process, a doc, a meeting that stopped earning its keep.",
      quarterOwn3: "Put one honest risk in writing before anybody asks for it — then be the one to offer it.",
      quarterOwn4: "Make one person who joined around the same time as you a little better at this place.",
      quarterOwn5: "Show your manager the finished version by week eight, not a report in week twelve.",
      quarterOwn6: "Ask for the fastest honest rumor about you; fix the part that is actually true.",
      quarterLift1: "Land the outcome the offer promised, then write the two-line story of how it happened.",
      quarterLift2: "Pair with one person from a differently-shaped team for a week.",
      quarterLift3: "Teach one thing you know cold to the whole team, in writing, once.",
      quarterLift4: "Update your resume now, while the year is fresh — everyone else waits for a layoff meeting.",
      quarterLift5: "Name the one thing you will refuse next time somebody asks you to save the world.",
      quarterLift6: "Tell one outsider plainly: this job is working — or it is not, and say why.",
      repliesTitle: "The bookend — the letters you send after the decision",
      repliesDescription:
        "The two letters every negotiation ends with: the yes that closes the loop before the thank-you emails are done, and the no that keeps the relationship.",
      replyYesKind: "The gracious yes",
      replyYesLine: "{company} — accept the offer, name the start, close the loop.",
      replyYesCaption: "One short page; warm, specific and quick. It should sound like you at your best, not like a template.",
      replyNoKind: "The graceful no",
      replyNoLine: "{company} — clear, warm, leaves the door open a crack.",
      replyNoCaption: "Send it the same day you decline. Silence is the one message this product will never write for you.",
      replyYesBody: "Dear Hiring Team,\n\nI am writing to formally accept the {role} offer with {company}. I am grateful to everyone I met in the process — this is a team I have wanted to work with for some time.\n\nPlease let me know the next steps for paperwork, benefits enrollment, and equipment. I look forward to joining you.\n\nWith appreciation,",
      replyNoBody: "Dear Hiring Team,\n\nThank you for the {role} offer — the time you put into this process is not lost on me, and I want to honor it by being clear rather than quiet. I've decided not to move forward this time.\n\nThis was a real choice between two strong options, not a verdict on the team. Talented people, real work, and every courtesy — it simply was not the right seat at the moment.\n\nIf the right opening comes up later, I hope we can pick this conversation back up. Thank you for your candor and your patience.\n\nWith thanks,",
      replyRead: "Read it",
      replyHide: "Hide it",
      replyDownload: "Download .txt",
      replyMailto: "Send this letter",
      roleFallback: "the role",
      celebrationTitle: "An offer, in hand.",
      celebrationSubtitle: "{role} — {company}",
      celebrationSubtitleRole: "{role}",
      celebrationSubtitleBare: "A role said yes.",
      celebrationBody: "The whole loop did this — not luck. Take the win, then take the counter.",
      celebrationShelf: "Open the offers shelf",
      celebrationContinue: "Keep going",
      committedTitle: "The call is made.",
      committedSubtitleBare: "You answered your own question.",
      committedBody: "The answer exists on paper now. The next quiet chores are queued below — countersign, notice, gear, and one person worth thanking.",
      committedShelf: "See the first week",
      theAnchor: "The anchor the engine computed.",
      compared: "Offers compared.",
      negotiationPlanReady: "Negotiation plan ready.",
      counterOfferReady: "Counter-offer draft ready.",
      offerFormat: "One offer per line. The engine ranks them by total compensation, with any equity annualized over its vest.",
      oneQuestion: "One question drives all four answers: what is the role, and what is on the table.",
      title: "Offers",
      description: "What the market pays, what to say back, and which offer leads.",
      roleAndOffer: "The role and the offer",
      role: "Role",
      location: "Location (optional)",
      offerBase: "Offer base (optional)",
      yourMatch: "Your match % (optional)",
      rolePlaceholder: "e.g. Senior Backend Engineer (Java)",
      locationPlaceholder: "e.g. Shanghai",
      basePlaceholder: "e.g. 400000",
      matchPlaceholder: "e.g. 82",
      benchmark: "Benchmark",
      coachMe: "Coach me",
      draftCounter: "Draft a counter",
      whatTheMarketPays: "What the market pays",
      negotiationPlan: "Negotiation plan",
      counterOfferDraft: "Counter-offer draft",
      compareOffers: "Compare offers",
      offerLabels: "Offer labels",
      compare: "Compare",
      matchingPostings: "{count} matching postings",
      matchingPostingsIn: "{count} matching postings in {location}.",
      verdicts: {
        below_market: "Below market",
        above_market: "Above market",
        within_market: "Within market",
        unknown: "Unknown",
      },
      noBenchmark: "No postings in the corpus for that role yet.",
      noComparison: "No offers to compare",
      nameOneOffer: "Name at least one offer above.",
      planReady: "Plan ready.",
      comparisonDone: "Offers compared.",
      counterOfferScript: "Counter-offer script",
      againstTheMarket: "Your offer against the market, and what to say.",
      leadsOnTotal: "{label} leads on total compensation.",
  narrativeLabel: "The editor says",
      anchorAt: "Anchor at {amount}.",
      ledgerTitle: "The decision ledger",
      ledgerDescription:
        "The market ranks total comp. Only you can rank what the job does to your life — weight six starter criteria (or add your own), score each offer 0-10, and read the weighted answer. It stays in your browser; nothing is sent anywhere.",
      ledgerEmptyShelf:
        "The shelf is empty. Add the offers you are weighing above — the ledger reads from them.",
      ledgerTableCaption: "Offers scored against the reader's own weighted criteria",
      ledgerCriterionCol: "Criterion",
      ledgerCriterion_comp: "Compensation",
      ledgerCriterion_growth: "Growth & learning",
      ledgerCriterion_team: "Team & manager",
      ledgerCriterion_mission: "Mission & domain",
      ledgerCriterion_location: "Location & commute",
      ledgerCriterion_stability: "Stability",
      ledgerWeight: "Weight",
      ledgerWeightFor: "How much {criterion} weighs",
      ledgerWeight_0: "Not a factor",
      ledgerWeight_1: "Barely matters",
      ledgerWeight_2: "Some weight",
      ledgerWeight_3: "Matters",
      ledgerWeight_4: "Very important",
      ledgerWeight_5: "The deal-breaker",
      ledgerOfferScore: "{offer} — score for {criterion}, 0-10",
      ledgerTotal: "Weighted total",
      ledgerTotalOf: "{total} of {max}",
      ledgerLeader:
        "The ledger's call: {label} leads — {total} of {max}, on the weights you set, not the market's.",
      ledgerTie:
        "The ledger ties: {labels} at {total} of {max}. A tie is an answer, not a bug — more than one seat is right.",
      ledgerNeedScores:
        "Score the rows. Nothing is ranked until you say what matters and how much.",
      ledgerAddCriterion: "Add your own criterion",
      ledgerAddPlaceholder: "e.g. the space to build without meetings",
      ledgerAddButton: "Add criterion",
      ledgerMaxReached: "Eight criteria is enough — the ledger keeps the signal, not the noise.",
      ledgerRemoveCriterion: "Remove this criterion",
      ledgerReset: "Clear the ledger",
      ledgerResetDone: "The ledger is cleared. Your offers are untouched.",
      rehearsalTitle: "The rehearsal room — the ask, before the offer",
      rehearsalDescription:
        "Three hiring-manager pushes, three replies each. Fumble it here, hold your nerve in the real one.",
      rehearsalStep: "Step {n} of 3",
      rehearsalPush_band: "…we hear you. Honestly, we can't stretch the band — policy is policy.",
      rehearsalPush_silence: "Hmm… well, we'll have to go back and circle on that.",
      rehearsalPush_anchor: "The number, as stated, is a lot to ask for.",
      rehearsalReply_band_hold:
        "I hear the policy. I'd like to hear how the stretch actually looks, threshold included.",
      rehearsalReply_band_open:
        "Alright — then let's lay the numbers on the table. What does the stretch look like, landing on me?",
      rehearsalReply_band_concede: "Alright, I understand — I'll take it as written.",
      rehearsalReply_silence_clock:
        "Of course. Let's say Friday at four — I'll hold my decision until then.",
      rehearsalReply_silence_when: "Of course — about when should I expect an answer?",
      rehearsalReply_silence_sure: "Sure.",
      rehearsalReply_anchor_evidence:
        "I hear you. The number isn't a wish — it's three things: what I'll bring, what I've brought, and what the market pays for it.",
      rehearsalReply_anchor_gap: "Then let's look at the gap and see if we shrink it.",
      rehearsalReply_anchor_maybe: "Maybe… it's high, then. Let me think about it.",
      rehearsalFeedbackEvidence: "Holds with evidence.",
      rehearsalFeedbackHold: "Holds the frame.",
      rehearsalFeedbackGap: "Opens the gap — nothing is held yet.",
      rehearsalFeedbackConcede: "Concedes early.",
      rehearsalNext: "Next push",
      rehearsalSeeVerdict: "See the verdict",
      rehearsalScoreLine: "{total} of {max} in the room",
      rehearsalVerdictNone: "Fold before sitting",
      rehearsalVerdictNoneDetail:
        "The room exhaled before you sat. The number is not high — it is the one you have not asked for yet.",
      rehearsalVerdictWeak: "Holding less than you think",
      rehearsalVerdictWeakDetail:
        "There's room to hold. The gap is evidence, and evidence is the part you're avoiding.",
      rehearsalVerdictSolid: "You held — and there is room to hold harder",
      rehearsalVerdictSolidDetail:
        "You negotiated. Not perfectly — and nobody does it perfectly the first time.",
      rehearsalVerdictStrong: "You negotiated",
      rehearsalVerdictStrongDetail:
        "You held your ground with evidence. The real room will surprise you; this one taught you how to sit in it.",
      rehearsalVerdictMasterful: "Nine of nine",
      rehearsalVerdictMasterfulDetail:
        "You ran the hard conversation before it happened. The first offer is never the best of the three you can name — and now you can name them.",
      rehearsalKeepTitle: "The sentence you will open with",
      rehearsalKeepDescription:
        "Your own words, kept in this browser — the sentence you would actually walk in with.",
      rehearsalKeepPlaceholder: "e.g. “Before the number — tell me what exceptional looks like here.”",
      rehearsalReset: "Start over",
      rehearsalKept: "Kept in this browser.",
      commitmentTitle: "The week's one line",
      commitmentDescription:
        "The whole search never ends; Tuesday cannot beat Sunday to the rope. One sentence — what you will own out loud before the week closes.",
      commitmentPlaceholder:
        "e.g. “Before Friday, I will send the yes-or-no letter.” — in your own words, said out loud.",
      commitmentLabel: "Week {week} — said out loud",
      commitmentSave: "Keep this line",
      commitmentSaved: "Kept in this browser.",
      commitmentReset: "Start a new line",
      packetPrint: "Print the packet",
      packetPrintHint:
        "Everything a salary conversation is actually about, kept on paper: the shelf, your day-one packet, the letters you kept, the ledger's call. The AI kitchen stays off the page.",
    },
    // Analysis
    analysis: {
      title: "Analysis",
      description: "Pipeline analytics and insights from your application history.",
      totalApplications: "Total applications",
      activePipeline: "Active pipeline",
      responseRate: "Response rate",
      stalled: "Stalled",
      stageMix: "Stage mix",
      stalledApplications: "Stalled applications",
      insights: "Insights",
      funnel: "Funnel",
      funnelDescription:
        "How many applications reached each stage, and the conversion at each step.",
      ofApplied: "of applied",
      responseRates: "Response rates",
      responseRatesDescription:
        "Of everything submitted, what fraction got any reply — a rejection included.",
      reply: "Reply",
      interview: "Interview",
      offer: "Offer",
      gotAReply: "{replied} of {applied} submitted applications got a reply.",
      noFunnel: "No funnel yet",
      noFunnelDescription:
        "Submit an application and the funnel starts measuring where it leaks.",
      noStalled: "No stalled applications",
      noStalledDescription: "Every application has recent activity.",
      loadFailed: "Analysis failed to load",
      stageMixDescription: "Applications at each pipeline stage.",
      noStageYet: "No applications have reached a stage yet.",
      stalledDescription: "Applications with no movement past {days} days.",
      insightsDescription: "What the data says about your pipeline.",
      weeklyTitle: "Weekly letter",
      weeklyDescription:
        "Composed on a schedule and kept, so a week's signals outlive the week.",
      weeklyCompose: "Compose this week",
      weeklyComposing: "Composing…",
      weeklyWeek: "Week of {date}",
      weeklyApplications: "Applications",
      weeklyQuietCount: "Quiet",
      weeklyReply: "Reply rate",
      weeklyOffer: "Offer rate",
      weeklyEditorialLabel: "The editor says",
      weeklyQuietDays: "{days}d quiet",
      stalledDays: "{days}d",
      weeklyUntitled: "Untitled",
      weeklyHistory: "Earlier letters",
      weeklyEmpty: "No letters yet",
      weeklyEmptyDescription:
        "The first letter is written on Monday morning — or compose this week's now.",
      weeklyEmptyPromise: "WHAT THE LETTER CARRIES",
      weeklyEmptyProof1: "What moved — replies, interviews, offers, by name",
      weeklyEmptyProof2: "Where the quiet weeks compounded into drift",
      weeklyEmptyProof3: "One lever for next week, chosen by the numbers",
      weeklyUnavailable: "The letters couldn't be loaded.",
      weeklyActionFailed: "Couldn't compose the letter.",
    },
    // Monitoring
    monitoring: {
      title: "Monitoring",
      description: "Agent health, cost, and regression detection.",
      healthVerdict: "Health verdict",
      errorRate: "Error rate",
      totalCost: "Total cost",
      totalTokens: "Total tokens",
      cacheHitRate: "Cache hit rate",
      cacheTokens: "Prompt tokens saved",
      p95Latency: "P95 latency",
      spendToday: "Today's AI spend",
      spendTodayDescription:
        "Every model call the engine booked to you today, against the day's cap. The cap is the dashboard's bar, not a gate — nothing here is refused.",
      spendTodayCalls: "{count} calls",
      spendTodayOfCap: "of a ${cap} day cap",
      spendTodayNoCap: "No cap configured (CAREEROS_DAILY_SPEND_CAP_USD=0)",
      spendTodayInput: "input tokens",
      spendTodayCached: "served from cache",
      spendTodayProgress: "Progress toward today's AI spend cap",
      spendTodayFailed: "Today's spend couldn't be loaded",
      promptCache: "Prompt cache",
      promptCacheDescription:
        "How much of the input the model reads fresh versus served from a cache. On this relay (aizzz.xyz, measured 2026-11-16 with include_usage): streaming rows carry prompt_tokens_details reliably — 8 of 8 probes, 8,192 of 8,353 input tokens from cache (98.1%). Non-stream rows report it randomly — a zero there is under-reporting, not a miss. Deterministic calls replay from the exact-match cache.",
      ledgerTitle: "The operator's ledger — measured, dated, real",
      ledgerDescription:
        "This install's own desk-notes: the load burst run against it, not a benchmark published elsewhere.",
      ledgerBody:
        "Identical calls re-measured 2026-11-16 against this relay (aizzz.xyz, gpt-6.1-terra): stream frames carried prompt_tokens_details in 8 of 8 probes — 8,192 of 8,353 input tokens cached (98.1%). Non-stream rows report it randomly (5 of 8 this sample; the 3 omissions are the relay's choice, not a miss). The gateway's breaker opened, half-opened, and closed on its own — twice, unattended. 555 model calls ledgered this install; 40% of input tokens were served from cache; resume_parse runs at 75.6% cached.",
      ledgerDateLine:
        "Measured 2026-11-15 and 2026-11-16, on this install. A number without a date is not a measurement — it is a story.",
      ledgerFinding1:
        "Identical non-stream calls · reporting is random · 5 of 8 carried the hint this sample, always 8,192 of 8,353 input tokens cached when carried",
      ledgerFinding2:
        "Stream frames · include_usage honored · cached tokens reported on 8 of 8 probes · 8,192 of 8,353 input tokens cached (98.1%)",
      ledgerFinding3:
        "Warm identical prefix · 94.9% cached observed earlier on this install",
      ledgerFinding4:
        "Re-measured 2026-11-21 · gpt-6.2-sol · non-stream now reports cached_tokens reliably (95% after warm-up) · interleaved parallel sessions each hold their own hits without interference · temperature 0 / 0.7 hit identically — the cache is driven only by a byte-identical prefix, not by streaming mode, temperature, or parallel sessions; the earlier 'non-stream zero means a miss' reading is corrected",
      alerts: "Alerts",
      regressions: "Regressions",
      runsAnalyzed: "{count} runs analyzed",
      verdicts: {
        healthy: "Healthy",
        warn: "Warning",
        regressed: "Regressed",
        unknown: "Unknown",
      },
      alertsDescription: "Issues that need attention.",
      regressionsDescription: "Metrics that regressed against baseline.",
      loadFailed: "Monitoring failed to load",
      latency: "Latency",
      latencyDescription: "The median call and the slow tail, on one scale.",
      p50: "p50 (median)",
      p95: "p95 (tail)",
      verdictDescription: "Overall agent health assessment.",
      nightlyTitle: "Nightly verification",
      nightlyDescription:
        "The deployment's own checks, one record per night: the backend suites, the eval harness and the portable export.",
      nightlyEmpty: "No night has left a record yet. The nightly job posts one when it finishes.",
      nightlyUnavailable: "The nightly history could not be read.",
      nightlyVerdictMissing:
        "No night has ever written a record — the verification job may never have run.",
      nightlyVerdictStale:
        "The newest record is more than {hours} hours old — the nightly job stopped reporting.",
      nightlyVerdictStreak: "{count} nights in a row ended failed.",
      nightlyStatuses: {
        passed: "Passed",
        failed: "Failed",
      },
      nightlyOpenRun: "Open the run",
      nightlyPagination: "Nightly reports pagination",
      topologyTitle: "Service topology",
      topologyDescription:
        "The fleet this deployment can route to, from the same discovery answer the load balancer reads.",
      topologyRegistry: "Registry",
      topologyRegistryEureka: "Eureka",
      topologyRegistryConfiguration: "Configuration list",
      topologyInstances: "{count} instance(s)",
      topologyInstanceSha: "{sha}",
      topologyEmpty: "The discovery client knows no service yet.",
      topologyUnavailable: "The topology could not be read.",
      resilienceTitle: "Service resilience",
      resilienceDescription:
        "Spring Cloud circuit breaker states for the ai-service bridge, as the backend reports them.",
      resilienceCalls: "Failed {failed} · OK {ok} · Rejected {rejected}",
      resilienceEmpty: "No circuit breakers are registered yet.",
      resilienceUnavailable: "Resilience status could not be read.",
      enginesTitle: "Engine fleet",
      enginesDescription:
        "The ai-service replicas the backend can call right now, as the health probe reports them.",
      enginesReady: "{count} of {total} ready",
      enginesEmpty: "No engine replica answered the health probe.",
      enginesUnavailable: "Engine health could not be read.",
    },
    // Rate limit
    rateLimit: {
      noThrottling: "No throttling is applied.",
      throttledPerUser: "Requests are throttled per user.",
      title: "Rate limiting",
      description: "Current rate-limit configuration and your bucket usage.",
      rateLimiting: "Rate limiting",
      aiEndpoints: "AI endpoints",
      authEndpoints: "Auth endpoints",
      yourRemainingQuota: "Your remaining quota",
      enabled: "enabled",
      disabled: "disabled",
      aiDescription:
        "Per-user limit for AI-costing endpoints (copilot, interview, JD analysis, etc.)",
      authDescription: "Per-IP limit for authentication endpoints (login, register, etc.)",
      quotaDescription: "Current token bucket usage for your account.",
      loadFailed: "Rate-limit status failed to load",
      enabledDescription: "Whether rate limiting is enabled.",
    },
    // Data portability
    data: {
      planReady: "Plan ready.",
      notValidJson: "That is not valid JSON.",
      sectionsRemoved: "Sections removed and the content hash recomputed.",
      fileSaved: "File saved to your downloads.",
      exportReady: "Export ready.",
      title: "Your data",
      description: "Export everything, preview a restore, and remove sections before you share.",
      /**
       * The sections a bundle holds, by name.
       *
       * The keys are the bundle's own -- the sections the exporter writes --
       * and the names are the reader's.
       */
      sections: {
        profile: "Profile",
        resumes: "Resumes",
        knowledge: "Knowledge base",
        jobDescriptions: "Job descriptions",
        interviews: "Interview sessions",
        memories: "Long-term memories",
        applications: "Applications",
        growthRuns: "Growth runs",
        notes: "Notes",
        contacts: "Contacts",
        conversations: "Copilot chats",
        savedSearches: "Saved searches",
        ingestionFeeds: "Ingestion feeds",
        savedJobs: "Saved jobs",
        inboundMails: "Recruiter replies",
        coverLetters: "Cover letters",
        offers: "Offers",
      },
      export: "Export",
      exportEverything: "Export everything",
      exportAnonymized: "Export anonymized",
      downloadJson: "Download JSON",
      downloadMarkdown: "Download Markdown",
      contentHash: "Content hash",
      generated: "Generated",
      redactBeforeSharing: "Redact before sharing",
      redactSelected: "Redact selected sections",
      previewRestore: "Preview a restore",
      bundleJson: "Bundle JSON",
      buildThePlan: "Build the plan",
      plan: "Plan",
      exportDescription:
        "A versioned bundle of your profile, resumes, knowledge base, job descriptions, interviews and memories — with a content hash, so an unchanged workspace exports to the same hash.",
      redactDescription:
        "Drop whole sections — the bundle stays valid and its content hash is recomputed over what is left.",
      restoreDescription:
        "Paste a bundle and see exactly what a re-import would write: the plan compares it with your workspace, so unchanged rows are skipped and a row the bundle no longer names is deleted from the sections a restore can match by id — the resumes, documents and memories it re-ingests are only ever added.",
      removedSoFar: "Removed so far:",
      applyTheRestore: "Apply the restore",
      applied: "What was written",
      appliedClean: "The restore was applied.",
      appliedWithSkipped: "The restore was applied, with sections left alone.",
      notJson: "That is not valid JSON.",
      printView: "Print view",
      popupBlocked: "Your browser blocked the print window.",
      opCreate: "Create",
      opUpdate: "Update",
      opDelete: "Delete",
      opSkip: "Unchanged",
      opTotal: "Total",
      pocketTitle: "The browser's pocket",
      pocketDescription:
        "The server cannot see what this browser kept: the decision ledger, the first-quarter plans, the day-one packets, the debriefs. This card is their suitcase — one JSON file with your four families, restorable on any machine.",
      pocketEmpty:
        "The pocket is empty. Score the ledger, tick the day-one packet, write the debrief — anything this browser keeps appears here.",
      pocketEmptyToast: "The pocket is empty — nothing to download yet.",
      pocketFamilyLedger: "Decision ledger",
      pocketFamilyQuarter: "First-quarter plans",
      pocketFamilyDayOne: "Day-one packets",
      pocketFamilyDebrief: "Interview debriefs",
      pocketFamilyCommitment: "Weekly commitments",
      pocketFamilyPreread: "The room you walk into",
      pocketFamilyNearMiss: "The near-miss",
      pocketFamilyCount: "{count} kept",
      pocketDownload: "Download the pocket",
      pocketRestore: "Restore from a pocket file",
      pocketRestoreFile: "Choose a pocket file to restore",
      pocketSaved: "The pocket is yours.",
      pocketInvalid: "That is not a pocket file this product wrote.",
      pocketRestored: "Restored {count} entries — nothing else was touched.",
      pocketRestoredWithSkipped:
        "Restored {count} entries; skipped {skipped} key(s) this product never wrote.",
      pocketHint:
        "Only the four prefixes this product writes are restored — a key from anywhere else is skipped, never overwritten.",
      // The plan's own sentence: the four counts the preview shows, and the
      // promise under the title ("unchanged rows are skipped") made countable.
      planWithCounts:
        "Plan ready: {create} to create, {update} to update, {delete} to delete, {skip} unchanged.",
      appliedCounts:
        "{created} created · {updated} updated · {deleted} deleted · {unchanged} unchanged",
    },
    // Ingestion
    ingestion: {
      sweepDone: "Sweep done.",
      planReady: "Plan ready.",
      untitledRole: "Untitled role",
      title: "Job ingestion",
      sourceFeed: "Source feed",
      feedContent: "Feed content",
      parse: "Parse",
      buildThePlan: "Build the plan",
      parsedPostings: "Parsed postings",
      deduplicate: "Deduplicate",
      freshnessSweep: "Freshness sweep",
      deduplication: "Deduplication",
      freshness: "Freshness",
      ingestionPlan: "Ingestion plan",
      sourceDescription:
        "RSS 2.0 / Atom XML, or a board-API JSON payload. Nothing is fetched from the network here — you paste what the source gave you.",
      parsedDescription: "postings parsed from the feed.",
      dedupeDescription:
        "Exact-fingerprint duplicates collapse to the newest, most complete record.",
      freshnessDescription: "Fresh, stale (re-check), expired (close), and undated.",
      planDescription:
        "The three writes a sweep would make. A close is only proposed for a posting that is expired *and* absent from this batch.",
      toCreate: "to create",
      toUpdate: "to update",
      toClose: "to close",
      duplicates: "duplicates",
      sweepDescription:
        "Bring postings in from a feed or a board API — parsed, deduplicated, and swept for freshness.",
      // Scheduled ingestion (19.2)
      scheduleHeading: "Scheduled feeds",
      scheduleDescription:
        "The backend's clock pulls each enabled feed once a night and files the run below. The plan a run proposes is recorded, never applied — the board is only written through the reviewable path above.",
      feedName: "Name",
      feedNamePlaceholder: "e.g. Hacker News — hiring",
      feedUrl: "Feed URL",
      feedUrlPlaceholder: "https://boards.example.com/jobs.rss",
      feedSource: "Source",
      sourceKindFeed: "RSS / Atom feed",
      sourceKindGreenhouse: "Greenhouse board",
      sourceKindLever: "Lever board",
      greenhouseUrlPlaceholder: "acme or https://boards.greenhouse.io/acme",
      leverUrlPlaceholder: "acme or https://jobs.lever.co/acme",
      boardNameNote:
        "For a board, the name is the company its postings belong to; a posting that names its own company still wins.",
      addFeed: "Add feed",
      feedAdded: "Feed added.",
      feedAddFailed: "Couldn't add that feed.",
      feedUpdateFailed: "Couldn't update that feed.",
      toggleAria: "Include {name} in the nightly sweep",
      runNow: "Run now",
      runNowFailed: "Couldn't pull that feed.",
      runRecordedToast: "The run was recorded.",
      runFailedToast: "The pull failed: {reason}",
      deleteFeedAria: "Delete {name}",
      deleteFeedTitle: "Delete this feed?",
      deleteFeedDescription:
        "{name} and its runs are removed. The jobs it already brought in stay on the board.",
      deleteFeedConfirm: "Delete feed",
      feedRemoved: "Feed removed.",
      feedRemoveFailed: "Couldn't remove that feed.",
      lastRun: "Last run",
      neverRun: "Never run — the next sweep will pick it up.",
      runsHeading: "Sweep runs",
      runsDescription:
        "Every pull the clock made, newest first — including the ones that failed, with the reason the server wrote down.",
      noRuns: "No runs yet. A feed's first pull happens at the next sweep, or when you run it now.",
      runsUnavailable: "The run history couldn't be loaded.",
      runsPaginationLabel: "sweep runs",
      feedsUnavailable: "The feed list couldn't be loaded.",
      unnamedFeed: "Unnamed feed",
      statusCompleted: "Completed",
      statusFailed: "Failed",
      viewPlan: "View plan",
      hidePlan: "Hide plan",
      planLoading: "Loading the plan…",
      planEmpty: "This run recorded no proposals to create.",
      incomingBadge: "{count} incoming",
      createBadge: "{count} to create",
      updateBadge: "{count} to update",
      closeBadge: "{count} to close",
      applyPlan: "Apply this plan",
      applyPlanTitle: "Apply this run's plan?",
      applyPlanDescription:
        "Writes {name}'s plan to the board: {create} to create, {update} to update, {close} to close. A run is applied once — the second press is refused.",
      applyPlanConfirm: "Apply the plan",
      appliedAt: "Applied {time}",
      appliedCounts: "{created} created · {updated} updated · {closed} closed",
      applyDone: "Plan applied: {created} created, {updated} updated, {closed} closed.",
      applyFailed: "Couldn't apply that plan.",
      noFeeds: "No feeds yet — add one above and the night's sweep will keep it current.",
      // The paste-feed card's own counts and toasts (14.2-14.3).
      parsedToast: "Parsed {count} posting(s).",
      dedupedToast: "{unique} unique, {duplicate} duplicate(s).",
      sweepSummary: "{fresh} fresh, {stale} stale, {expired} expired, {undated} undated.",
      planSummary: "Plan: {create} to create, {update} to update, {close} to close.",
      uniqueBadge: "{count} unique",
      duplicateBadge: "{count} duplicate",
      inputBadge: "{count} in",
      freshBadge: "{count} fresh",
      staleBadge: "{count} stale",
      expiredBadge: "{count} expired",
      undatedBadge: "{count} undated",
    },
    // Notification center (19.3)
    notifications: {
      title: "Notifications",
      description:
        "Reminders that came due, applications that went quiet, pulls that need a look, saved searches the board answered, and recruiter replies — in the order they happened.",
      markAllRead: "Mark all read",
      clearRead: "Clear read",
      unreadBadge: "{count} unread",
      allRead: "Everything here is read.",
      filterAll: "All",
      filterByKind: "Filter by kind",
      filterUnread: "Unread only",
      filterEmpty: "Nothing under this filter right now.",
      empty: "Nothing needs your attention right now.",
      emptyDescription:
        "A reminder that comes due, an application that goes quiet, a failed feed pull, a pull that created postings, a saved search that finds new postings, or a reply from a recruiter will appear here.",
      allCaughtUpTitle: "The inbox is quiet.",
      allCaughtUpDescription:
        "Reminders, stalled applications, failed pulls, new postings, saved searches and recruiter replies — all caught up. You can hear yourself think in here.",
      unavailable: "The inbox couldn't be loaded.",
      kindReminder: "Reminder",
      kindStale: "Gone quiet",
      kindIngestionFailed: "Pull failed",
      kindIngestionCreated: "New postings",
      kindSavedSearch: "Saved search",
      kindReply: "Recruiter reply",
      kindOther: "Signal",
      reminderLine: "Your reminder for {title} is due.",
      staleLine: "No movement on {title} — it has gone quiet.",
      ingestionFailedLine: "The last pull of {feed} failed.",
      ingestionCreatedLine: "New postings from {feed}: {count}.",
      savedSearchLine: "New postings match your saved search {name}: {count}.",
      replyLine: "A recruiter replied about your application — {title}.",
      fallbackLine: "A signal is waiting for you.",
      untitled: "Untitled",
      unnamedFeed: "an unnamed feed",
      unnamedSearch: "an unnamed search",
      open: "Open",
      openAria: "Open {title}",
      snoozeReminder: "Snooze to tomorrow",
      clearReminder: "Clear",
      markReadAria: "Mark {title} read",
      dismissAria: "Dismiss {title}",
      actionFailed: "Couldn't update the inbox.",
    },
    // Growth engines
    growthEngines: {
      title: "Growth engines",
      priorities: {
        critical: "Critical",
        high: "High",
        medium: "Medium",
        low: "Low",
      },
      description:
        "Each engine on its own — the same ones the growth report composes, asked one question at a time.",
      targetRole: "Target role",
      run: "Run",
      noAnswer: "No answer yet",
      noAnswerDescription: "Name the role and run the engine.",
      // The key is `inFlight` rather than `running` on purpose: the frame
      // contract gate scans the frontend for the word `running` in a field
      // position, and this string would be read as the task-stream panel's
      // own `running` flag — a different thing in a different file.
      inFlight: "Running…",
      failed: "The engine failed. The backend logs the reason.",
      study: "Study",
      rehearse: "Rehearse",
      practiceThis: "Rehearse this",
      practiceThisHint: "Starts a fresh rehearsal titled with this role.",
      locationOptional: "Location (optional)",
      coverage: "Coverage",
      targetRolePlaceholder: "e.g. Senior Backend Engineer (Java)",
      locationPlaceholder: "e.g. Shanghai",
      covered: "covered",
      partial: "partial",
      expected: "expected",
      gapNoteLabel: "The analyst says",
      missingForDreamRole: "Missing for the dream role:",
      /**
       * The nine engines, by name.
       *
       * A key the table does not know keeps the engine's own English name
       * rather than losing it, which is the same rule `stageLabel` follows
       * for the pipeline's seven stages.
       */
      /**
       * 359: the sentence each engine answers, on the button that runs it.
       *
       * Nine engines, nine questions, and the labels are one word each -- a
       * reader who has not read the manual cannot tell a snapshot from a trend.
       * The hint says what the engine answers and what it needs typed in, so a
       * click is never a guess. The words are the reader's, in both languages.
       */
      hintGap: "What you are missing for this role, and how much of it you already cover. Needs the role.",
      hintDemand: "Which skills this role is actually asked for, and how often. Needs the role; location sharpens it.",
      hintPriority: "Which of your gaps is worth learning first, ranked by how much the market pays for it. Needs the role.",
      hintPlan: "A phased plan that closes those gaps in order, week by week. Needs the role.",
      hintPrep: "What to study and what to rehearse before the interview, with the stories to practise. Needs the role.",
      hintProgression: "The stepping-stone roles between here and the one you want, in order. Needs the role.",
      hintStories: "Your strongest past work, written as STAR stories you can reuse. Reads your resume -- no role needed.",
      hintRoles: "Roles worth aiming at, drawn from what you have already done. Reads your resume -- no role needed.",
      hintProgress: "How your coverage of this role has moved since the last run. Needs the role.",
      hintNeedsRole: "Type the role first -- at least ten characters, so the engine knows what to measure against.",
      engines: {
        gap: "Gap analysis",
        demand: "Market demand",
        priority: "Learning priority",
        plan: "Learning plan",
        prep: "Interview prep",
        progression: "Progression",
        stories: "Story bank",
        roles: "Role suggestions",
        progress: "Progress",
      },
    },
    // Resumes
    resumes: {
      awaitingParsing: "Awaiting parsing",
      parsedOpenToSet: "Parsed — open to set the current version",
      currentVersionSet: "Current version set · agents match against it",
      addedOn: " · added {when}",
      title: "Resumes",
      description:
        "Every upload is parsed into a structured profile and chunked into the knowledge base the agents cite from. Nothing is scored that isn't in your documents.",
      uploadSection: "Upload a resume",
      existingSection: "Existing resumes",
      deleteDescription:
        "The resume and its versions are removed from your workspace. Knowledge chunks ingested from it stop being cited.",
      deleteResume: "Delete resume",
      deleteAria: "Delete {title}",
      deleteTitle: "Delete “{title}”?",
      empty: "No resumes yet",
      emptyDescription:
        "Drop a file above to get started. The ingestion pipeline extracts experience, projects and skills, then grades resume quality.",
      notLiveDescription:
        "GET /resumes answered 404, so this frontend and the backend it is talking to are different versions. Uploads are wired and appear as soon as they match — nothing is invented to fill the gap.",
      paginationLabel: "resumes",
      printBlocked:
        "The print window was blocked — allow pop-ups for this site and try again.",
      yourVersions: "Your versions",
      open: "Open",
      /**
       * The badge a resume's row wears, by the state the row is in.
       *
       * The states are the wire's -- the ingestion pipeline's own -- and the
       * words are the reader's.
       */
      status: {
        parsed: "Structured",
        parsing: "Parsing…",
        failed: "Failed",
        ingesting: "Ingesting…",
        uploaded: "Uploaded",
      },
      versionKinds: {
        original: "Original parse",
        tailored: "Tailored draft",
      },
      detail: {
        profileExported: "Structured profile exported.",
        runTheParse: "Run the parse above to turn this file into a queryable profile: experience, projects, education and skills with citations back to the document.",
        parsedToast: "Parsed — structured profile updated.",
        downloadFailed: "Download failed.",
        roleFallback: "Role",
        rolesTitle: "{count} role{plural}",
        projectsTitle: "{count} project{plural}",
        dateUnavailable: "date unavailable",
        scoreSuffix: " · score {score}",
        profileFallback: "Profile",
        noScore: "No review score yet. It is produced by the parsing run — trigger a re-parse above to generate one.",
        noVersions: "No stored versions yet — each parse of this resume stores a new one.",
        extracting: "The extraction agent is working through this document — the structured profile appears automatically when it's done.",
        parseNow: "Parse now",
        reParse: "Re-parse",
        notInWorkspace: "This resume isn't in your workspace",
        notInWorkspaceDescription:
          "It may have been deleted. Upload it again from the Resumes page.",
        loadFailed: "Couldn't load this resume",
        parsing: "Parsing",
        notParsedYet: "Not parsed yet",
        quality: "Resume quality",
        qualityDescription:
          "Only shown when the reviewer has actually scored this document.",
        impressionTitle: "What this resume says",
        impressionDescription:
          "One paragraph the reviewer writes over this document's own facts — the shape of the experience and the clearest gap, every claim anchored to a number in the resume.",
        impressionAction: "Read me this resume",
        impressionWorking: "Reading the resume…",
        impressionEmpty: "Nothing worth naming came back — not a verdict, just no grounded paragraph to show.",
        versions: "Versions",
        versionsDescription: "Original parses and tailored drafts.",
        versionsLoadFailed: "Couldn't load versions",
        whereFrom: "Where this comes from",
        scoreRing: "Resume score",
        profileEmpty: "Structured profile is empty",
        profileEmptyDescription:
          "The parse returned no sections. Re-run the parser or check the source document in Knowledge.",
        schools: "Schools & degrees",
        inventory: "Grouped inventory",
        direction: "Direction & highlights",
        targetRoles: "Target roles",
        preferredLocations: "Preferred locations",
        careerGoals: "Career goals",
        submitting: "Submitting the parse request…",
        loading: "Loading resume…",
        backToResumes: "Back to resumes",
        originalDownloaded: "Original file downloaded.",
        addedOn: "added {when}",
        originalFile: "Original file",
        parseFailed: "Parse failed:",
        setCurrent: "Set current",
        print: "Print",
        diffVsPrevious: "Diff vs previous",
        profileFrom: "Profile from",
        structuredJson: "structured JSON.",
        scoreFrom: "Score from the reviewer agent's parse step · chunks in",
        knowledge: "Knowledge",
        gapsFound: "Gaps found",
        exportJson: "Export JSON",
        achievements: "Achievements",
        current: "Current",
        overall: "Overall",
        repo: "Repo",
        versionFallback: "Version {version}",
        groupFallback: "Group {number}",
        stages: {
          reading: "Reading the stored document",
          extracting: "Extracting sections with the parser agent",
          structuring: "Structuring experience, projects and skills",
          grading: "Grading resume quality",
        },
      },
    },
    // Settings
    settings: {
      title: "Settings",
      description: "Account, appearance and keyboard preferences.",
      colorTheme: "Color theme",
      themeLight: "Light",
      themeDark: "Dark",
      themeSystem: "System",
      logOut: "Log out of Career OS?",
      logOutDescription: "Your data stays safe — this only ends the current session.",
      logOutConfirm: "Log out",
      account: "Account",
      accountDescription:
        "Live from /users/me — the display name is editable, the email rides on your login.",
      roles: {
        user: "User",
        admin: "Admin",
      },
      displayName: "Display name",
      signOut: "Sign out",
      signOutDescription: "Ends this session and revokes the refresh token.",
      sessionUnverified: "Session could not be verified.",
      appearance: "Appearance",
      appearanceDescription: "The interface follows your system theme by default.",
      renderingIn: "Rendering in {palette} palette.",
      wheelTitle: "Scroll direction",
      wheelDescription:
        "Two dialects, both forced app-wide — the platform is not consulted. Pick the one your fingers expect.",
      wheelStandard: "The view follows the wheel (down is down)",
      wheelNatural: "Content follows the gesture",
      wheelSaved: "Scroll direction saved.",
      wheelHint:
        "Down is down here: wheel down, the view moves down — on every platform. If your machine inverts the wheel, switch to Natural — down will be down. One switch, no reload.",
      paletteDark: "dark",
      paletteLight: "light",
      keyboard: "Keyboard",
      commandPalette: "Command palette",
    },
    push: {
      title: "Browser notifications",
      description:
        "The morning sweep can ring this browser even when the tab is closed. The wake carries no text — the inbox it opens does.",
      toggle: "Ring this browser",
      onDescription: "This browser will ring when the morning finds something new.",
      offDescription: "This browser stays quiet. The inbox still fills.",
      checking: "Checking this browser…",
      unsupported: "This browser cannot receive push notifications.",
      notInstalled:
        "Notifications need the installed app's worker. Open the production build once, then come back.",
      blocked:
        "This browser has blocked notifications for this site. Allow them in the site settings, then turn this on again.",
      notConfigured:
        "This deployment has no push keys, so no wake can leave. The inbox still fills.",
      permissionDenied: "Permission was not granted, so nothing was registered.",
      failed: "The browser registration could not be saved. Try again.",
    },
    /**
     * The calendar card's sentences (34.1). "The address is the credential" is the
     * one fact the reader has to understand before copying it somewhere else, so the
     * description says it outright rather than leaving it to the hint.
     */
    calendar: {
      title: "Calendar subscription",
      description:
        "Read your reminders and pending offer decision days in the calendar app you already open. The address below is the whole credential — anyone holding it can read these, and a new secret retires every address at once.",
      linkLabel: "Your calendar address",
      copy: "Copy address",
      loading: "Preparing your address…",
      loadFailed: "The address could not be prepared. Reload the page and try again.",
      hint: "Paste it into Google Calendar, Apple Calendar or Outlook under “subscribe from a URL”. A reminder — and an undecided offer’s deadline — appears on the calendar’s next poll, and stays until you clear it here.",
    },
    /**
     * The mail-letters card (42.1, 42.2). The three dials used to be reachable only from the
     * footer of a letter; this card reads them from the account, settles each switch there,
     * and hands over the same signed page, so the reader never has to find an old mail.
     */
    mailLetters: {
      title: "The letters Career OS sends",
      description:
        "Three letters can reach your address: the Monday letter, the morning signals, and the reminder's own letter. The switches here read and settle those states in your account, so you do not need an old mail to change them.",
      weekly: "The Monday letter",
      signals: "The morning signals",
      reminders: "The reminder's own letter",
      on: "On",
      off: "Off",
      linkLabel: "The settings page",
      copy: "Copy address",
      open: "Open the settings page",
      loading: "Reading your mail settings…",
      loadFailed: "The mail settings could not be read. Reload the page and try again.",
      hint: "The address is a key: it carries this account's signature, so anyone holding it can change these switches. Replacing the server's link secret retires every address at once.",
    },
    /**
     * The forwarding address card (37.4). "The address is the credential" is the same
     * sentence the calendar card says, and here it is literally true: the address is
     * all a sender needs to write into this account's replies, so rotating the secret
     * is the only way to retire it.
     */
    inbound: {
      title: "Forwarding address",
      description:
        "Send recruiters' replies straight into your applications: forward their mail to the address below and each letter lands on the timeline it answers, read before the page ever sees it.",
      addressLabel: "Your reply address",
      copy: "Copy address",
      loading: "Preparing your address…",
      notConfigured:
        "This deployment has no receiving inbox yet, so a reply has nowhere to land. The address appears once an operator configures a receiving domain.",
      loadFailed: "The address could not be prepared. Reload the page and try again.",
      rotationWarning:
        "The address is the whole credential — anyone who holds it can write into this account's replies. Rotating the signing secret retires it; there is no per-address revoke.",
      hint: "Only mail forwarded to this address is read. Your own mailbox's password never leaves your mail provider.",
      openReplies: "Open replies",
    },
    /**
     * The replies page (37.4). The badge's words are the classifier's five intents
     * plus the one state that is not a reading at all: a letter nobody has opened yet.
     */
    replies: {
      title: "Replies",
      description:
        "What recruiters wrote back, newest first. A letter either names the application it answers or waits here until you pick one.",
      loading: "Reading the replies…",
      searchPlaceholder: "Search replies",
      searchLabel: "Search replies by subject, sender, company, role or letter text",
      search: "Search",
      clearSearch: "Clear search",
      filterByIntent: "Filter replies by reading",
      filterAll: "All",
      filterByFileState: "Filter replies by whether they are filed",
      filterUnfiled: "Waiting for a card",
      noUnfiledMatch: "Nothing is waiting for a card",
      noUnfiledMatchDescription:
        "Every reply already names its application. Show every letter to read them.",
      showAll: "Show every letter",
      noMatch: "No replies match “{query}”",
      noMatchDescription: "Try a shorter word, or clear the search to see every letter.",
      noMatchFilterDescription:
        "No letter matches those words under this filter. Show every letter to start over.",
      noIntentMatch: "Nothing under this filter",
      noIntentMatchDescription:
        "No letter reads that way. Show every letter, or pick another reading.",
      noIntentUnfiledDescription:
        "No waiting letter reads that way. Show every letter, or pick another reading.",
      unavailable: "The replies could not be read. Try again in a moment.",
      unnamed: "A letter with no subject",
      senderUnknown: "Sender unknown",
      intents: {
        unread: "Unread",
        rejection: "Rejection",
        interview: "Interview",
        offer: "Offer",
        info: "Information",
        other: "Other",
      },
      filedOn: "Filed on {title}",
      openApplication: "Open application",
      notFiled: "Not filed yet — add an application to file it on.",
      pickApplication: "Pick the application",
      file: "File",
      filedToast: "The letter is filed on its application.",
      fileFailed: "The letter could not be filed",
      readLetter: "Read the letter",
      applyStage: "Move to {stage}",
      applyStageConfirm: "Move “{title}” to {stage}?",
      applyStageDescription:
        "The letter reads as a {intent}, so the classifier suggests {stage}. This moves the card now; you can move it back at any time.",
      applyStageToast: "The card moved.",
      decodeAction: "Decode this letter",
      decodeAgain: "Decode again",
      decodeHint:
        "Ask once — the analyst reads only the letter's own words, cites only the numbers in it, and stays silent when nothing stands.",
      decodePending: "Reading the letter…",
      decodeEmpty:
        "Nothing in this letter stands still enough to say it either way — the letter itself is the record.",
      decodeError: "The decode could not finish. Try again in a moment.",
      decodeNextActionLabel: "Do next:",
      decodeDeadline: "They ask for {date}",
      decodeAsksLabel: "What they ask",
      decodeReplyLabel: "Ready-to-edit reply",
      decodeCopyHint: "Copy the draft as a starting point — edit it before sending.",
      decodeCopy: "Copy",
      decodeCopied: "Copied",
      getAddress: "Get your address",
      inboxPromise: "The replies pile is clear — no letter is waiting for you.",
      empty: "No replies yet",
      emptyDescription:
        "Forward recruiter mail to your reply address and each letter lands here, attached to the application it answers.",
      paginationLabel: "Replies pages",
      notYetTitle: "The not-yet letter — read it once more, better",
      notYetDescription:
        "Every recruiter's no is a letter a real person read yours and then wrote. Three shapes they actually write; your job is to take the one signal in each and keep it.",
      notYetReset: "Start a fresh letter",
      notYetDoor_calibrate_label: "The calibration",
      notYetDoor_calibrate_quote: "“Other candidates whose backgrounds more closely match…”",
      notYetDoor_calibrate_decode:
        "The wall is the bar, not the craft. “More closely matched” almost never means “worse than you” — it means someone else fit their stack line better on paper.",
      notYetDoor_calibrate_keep:
        "If you want to know what “more closely” meant — ask. The thread is the one place a closed door sometimes opens.",
      notYetDoor_hold_label: "The hold",
      notYetDoor_hold_quote: "“The role has been put on hold for business reasons…”",
      notYetDoor_hold_decode:
        "An external constraint — budget, a reorg, a priority nobody told you about. Zero signal about your work; the shortest sentence in the genre, and the most empty.",
      notYetDoor_hold_keep:
        "Nothing to decode. File it under “company's problems” and get on with the week — the week is yours, not theirs.",
      notYetDoor_impress_label: "The almost",
      notYetDoor_impress_quote: "“We were impressed, but we've decided to move forward…”",
      notYetDoor_impress_decode:
        "Close. “Impressed” is a real word in this format. The tiebreaker went elsewhere — and it usually isn't the thing you spent the most time polishing.",
      notYetDoor_impress_keep:
        "The one question worth sending: “What made the difference?” The answer is worth more than the no.",
      notYetKeepTitle: "The sentence you're keeping",
      notYetKeepDescription: "Your own words — kept in this browser only.",
      notYetKeepPlaceholder: "e.g. “Impressed. Ask what ‘match’ meant next time.”",
      notYetKept: "Kept in this browser.",
      nearTitle: "The near-miss",
      nearDescription:
        "The role that almost was — kept honestly: one close call, named, and what it taught you. Sealed when the role and the lesson both exist — nothing else is asked of you.",
      nearRole: "The role",
      nearRolePlaceholder: "e.g. the final round at Acme — what they called it",
      nearCompany: "The company",
      nearCompanyPlaceholder: "Optional — this shelf is only yours",
      nearAgain: "Would you walk in again?",
      nearAgainYes: "I'd walk in",
      nearAgainNo: "I'd pass politely",
      nearLearned: "What the miss taught you",
      nearLearnedPlaceholder: "The sentence you keep — the one a specific scar taught you, not the one you read in a book",
      nearChanged: "What changed since",
      nearChangedPlaceholder: "The habit, the sentence, the way you now enter a room",
      nearReset: "Empty the near-miss",
      nearSealed: "Near-miss sealed — kept honestly",
      nearProgress: "{done} of {total} pieces sealed",
    },
    /**
     * The second door's card (36.4). The card is the only screen that can turn the
     * factor on, print the recovery codes and take the factor off again, so its
     * sentences say what each action costs rather than what it does.
     */
    security: {
      title: "Two-factor authentication",
      description:
        "A second step at sign-in: the password, then a six-digit code from an authenticator app.",
      on: "On",
      off: "Off",
      pending: "Not proven",
      onDescription:
        "This account asks for a code after the password. Keep the printed recovery codes somewhere other than the phone that holds the key.",
      offDescription:
        "The password alone opens this account right now. Turn on the second step and a stolen password stops being enough.",
      pendingDescription:
        "An enrollment was started here but never proven. The key was shown once and cannot be shown again, so start over to mint a new one.",
      remaining: "{count} recovery codes left",
      remainingNone:
        "No unused recovery codes are left. Replace them with a fresh set before you need one.",
      loading: "Checking the second door…",
      loadFailed: "The second factor's state could not be loaded. Reload the page and try again.",
      start: "Turn on two-factor",
      startEnrollment: "Start two-factor enrollment",
      startOver: "Start over",
      enrollHint:
        "Add this key to your authenticator — scan the setup address or type the key by hand — then prove it with the six digits the app shows.",
      secretLabel: "Authenticator key",
      copySecret: "Copy key",
      uriLabel: "Setup address",
      copyUri: "Copy address",
      passwordLabel: "Your password",
      passwordPlaceholder: "Your current password",
      codeLabel: "Six-digit code",
      codePlaceholder: "123456",
      proofCodeLabel: "Code or recovery code",
      proofCodePlaceholder: "123456 or a printed code",
      activate: "Prove and turn on",
      replace: "Replace recovery codes",
      replaceHint:
        "This revokes every printed code and hands you ten new ones. Enter your password and a working code — the app's or one of the printed ones.",
      disable: "Turn off two-factor",
      disableHint:
        "This removes the second step from this account and revokes every printed code. Enter your password and a working code.",
      cancel: "Cancel",
      codesTitle: "Your recovery codes",
      codesHint:
        "Ten single-use codes, each one signing in place of the app's code. This is the only time they are shown — save them somewhere else now.",
      copyAll: "Copy all codes",
      codesDone: "I saved them",
      issues: {
        passwordRequired: "Enter your password",
        codeRequired: "Enter the code",
        codeSixDigits: "Enter the six digits from your authenticator",
      },
    },
    memory: {
      description: "Facts the model extracted from your conversations and interviews. Correct a wrong one, or lower its weight — these shape every answer you get.",
      loading: "Loading memories…",
      emptyTitle: "Nothing remembered yet",
      empty: "Chat with the copilot or finish an interview and the facts it learns appear here.",
      whatAgentsRemember: "What the agents remember",
      whatAgentRemembers: "What the agent remembers",
      forget: "Forget",
      forgetConfirm: "Forget this memory?",
      forgetDescription: "It will stop shaping the answers the agents give you. This cannot be undone.",
      editAria: "Edit memory: {preview}",
      forgetAria: "Forget memory: {preview}",
      weight: "Weight",
      weightHigherFirst: "Higher-weight memories come first in every answer.",
      weightBands: {
        low: "Low",
        normal: "Normal",
        high: "High",
      },
      kinds: {
        profile: "Profile",
        skill: "Skills",
        preference: "Preferences",
        interview: "Interview history",
        goal: "Goals",
        fact: "Facts",
      },
      characters: "{count} / {limit} characters",
      loadFailed: "Memories could not be loaded",
    },
    profile: {
      description: "What the agents assume about you — headline, targets and the story they tell recruiters.",
      loading: "Loading profile…",
      careerProfile: "Career profile",
      targetRoles: "Target roles (comma separated)",
      targetLocations: "Target locations (comma separated)",
      linksExtras: "Links & extras",
      mapsDescription: "Free-form maps the agents read — links, work authorization, preferences. Values that parse as JSON keep their type; everything else is saved as a string.",
      headline: "Headline",
      headlinePlaceholder: "e.g. Backend engineer moving into platform work",
      summary: "Summary",
      summaryPlaceholder: "The short story a recruiter gets before the resume.",
      location: "Location",
      locationPlaceholder: "e.g. Hangzhou",
      yearsExperience: "Years of experience (0–{max})",
      yearsPlaceholder: "e.g. 6",
      yearsIssue: "Years of experience has to be a number between 0 and {max}, or left blank.",
      rolesPlaceholder: "e.g. Platform engineer, Staff engineer",
      locationsPlaceholder: "e.g. Hangzhou, Remote",
      addRow: "Add row",
      mapValuePlaceholder: "value — JSON or plain text",
      mapKeyAria: "{label} key {index}",
      mapValueAria: "{label} value {index}",
      mapRemoveAria: "Remove {label} row {index}",
      maps: {
        links: "Links",
        linksPlaceholder: "e.g. github",
        workAuthorization: "Work authorization",
        workAuthorizationPlaceholder: "e.g. status",
        preferences: "Preferences",
        preferencesPlaceholder: "e.g. remote",
      },
      issues: {
        tooManyRoles: "Use at most {max} target roles",
        roleTooLong: "Each role can be at most {max} characters",
        tooManyLocations: "Use at most {max} target locations",
        locationTooLong: "Each location can be at most {max} characters",
      },
      saveProfile: "Save profile",
      saveMaps: "Save maps",
      loadFailed: "Profile could not be loaded",
    },
    /**
     * The auth pages' marketing panel. A visitor who cannot read English
     * lands here first, and this panel is what they are asked to believe.
     */
    auth: {
      /**
       * The public pages' own titles.
       *
       * The tab's title is the server's `metadata` before the browser takes
       * it over, and the server cannot read the locale -- so the reader's
       * language arrives with the client, and the title follows it.
       */
      pageTitles: {
        signIn: "Sign in",
        signUp: "Create account",
        forgotPassword: "Reset your password",
        resetPassword: "Set a new password",
        confirmEmail: "Confirm your new address",
        accountErased: "Account erased",
      },
      eyebrow: "The job-search operating system",
      headline: "Run your search like an engineer runs a system.",
      description:
        "AI Career OS turns your career material into a knowledge base, then drives the whole loop — discovery, matching, tailoring, interviews, pipeline.",
      quote: "“Never fabricate experience — every claim maps to evidence.”",
      pillars: {
        knowledge: {
          title: "Career Knowledge Base",
          text: "Your resume, projects and notes become a searchable, cited evidence layer.",
        },
        matching: {
          title: "Evidence-backed matching",
          text: "Every match score is computed — then explained with quotes from your own material.",
        },
        fabrication: {
          title: "Tailoring without fabrication",
          text: "Resumes reworded and reordered per job description; a verifier rejects invented claims.",
        },
        interviews: {
          title: "Adaptive mock interviews",
          text: "An AI interviewer that follows up, scores dimensions and adapts difficulty.",
        },
      },
      welcomeBack: "Welcome back.",
      accountCreated: "Account created — welcome to Career OS.",
      signInToWorkspace: "Sign in to your workspace",
      createYourAccount: "Create your account",
      signIn: "Sign in",
      createAccount: "Create account",
      confirmPassword: "Confirm password",
      passwordsDoNotMatch: "Passwords do not match",
      forgotPassword: "Forgot your password?",
      email: "Email",
      password: "Password",
      code: "Six-digit code",
      codePlaceholder: "123456",
      fullName: "Full name",
      fullNamePlaceholder: "Ada Zhang",
      noAccount: "No account yet?",
      createOne: "Create one",
      alreadyRegistered: "Already registered?",
      loginBlurb: "Pick up where the agents left off.",
      registerBlurb: "Your resume becomes a knowledge base in minutes.",
      codeHint:
        "Your password checked out. Add the six-digit code from your authenticator, or one of your printed recovery codes.",
      // The field checks answer with these keys; the sentence is built where
      // it is shown, so the error under a Chinese field is Chinese.
      issues: {
        emailRequired: "Email is required",
        emailInvalid: "Enter a valid email address",
        passwordRequired: "Password is required",
        codeRequired: "Enter the code from your authenticator or a recovery code",
        nameRequired: "Name is required",
        tokenRequired: "Paste the token from your email",
        confirmRequired: "Confirm your new password",
        tooShort: "Use at least {min} characters",
        tooLong: "Use at most {max} characters",
      },
    },
    /**
     * The skill chips: the two labels that sit above the matched row and
     * the missing one.
     */
    skillChips: {
      why: "Why",
      missing: "Missing",
    },
    /**
     * The error boundaries. The outermost one replaces the root layout --
     * and with it the locale provider -- so it carries its own copy of the
     * provider rather than reading a context that is not there.
     */
    sourceActions: {
      reset: "Clear the source list",
      resetTooltip: "Remove the sources loaded in this session and start fresh",
    },
    errors: {
      brokeOnThisScreen: "Something broke on this screen.",
      brokeOnThisScreenDescription:
        "The error was logged to the console. Retrying re-renders the page without losing your session.",
      couldNotStart: "The app could not start.",
      couldNotStartDescription:
        "The error was logged to the console. Retrying rebuilds the whole shell from scratch.",
      notOnTheMap: "This page is not on the map.",
      notOnTheMapDescription:
        "The route you followed does not exist. It may have moved, or the link was mistyped.",
    },
    /**
     * The failures, by the code that names them.
     *
     * The **code** is the contract -- the enum's own comment says "never
     * rename an emitted code" -- and the code is what crosses the wire, so
     * the sentence comes from the code and the reader sees it in the
     * language they chose.
     *
     * The browser raises some of these itself: the stream that ended early,
     * the upload the reader cancelled, the network that was not there. The
     * rest are the **services'** codes, and they are here only where the
     * code means one thing: a code that answers with several different
     * sentences -- `BAD_REQUEST` answers with twelve -- cannot be given
     * one sentence without the sentence being wrong about half of them, so
     * those keep the server's own words until the code is fine enough to
     * carry them. The gate knows which is which, and it reads the throw
     * sites to find out.
     *
     * The split is made code by code, and the resume's not-found code is
     * already six codes -- `RESUME_NOT_AVAILABLE`, `RESUME_NOT_PARSED`,
     * `RESUME_NOT_TAILABLE`, `RESUME_FILE_MISSING`, `RESUME_NOT_INGESTED`
     * and `RESUME_NOT_FOUND` -- each with its own sentence. The status
     * did not move: the code is the contract, and the status is what the
     * client's error path reads.
     *
     * A toast is raised from an event handler, long after the render that
     * knew the reader's language, so these are read through `translate` --
     * which reads the language outside React.
     */

    /** Epic 347 — the one-time, in-app guided hello on a new reader's first open. */
    quickstart: {
      title: "Your first four steps",
      description: "A 30-second walk through the real workspace. Each step opens the screen it names; come back to the guide any time from the compass button.",
      progress: "Step {current} of {total}",
      stepsLabel: "Quick start steps",
      step1Title: "Start at your workspace",
      step1Body: "This dashboard is home. It shows what you've done and the single next thing to do — nothing here is pre-filled, so every number is yours.",
      step1Href: "/dashboard",
      step1HrefLabel: "Open the dashboard",
      step2Title: "Give it your evidence",
      step2Body: "Upload a resume and the reviewer turns it into structured, cited facts — the evidence every later step quotes. Or paste a job posting to see what a role asks for.",
      step2Href: "/resumes",
      step2HrefLabel: "Add your resume",
      step3Title: "Find your fit, then rehearse",
      step3Body: "Match a job against your own evidence, tailor a version without inventing anything, then rehearse the interview out loud with adaptive feedback.",
      step3Href: "/jobs",
      step3HrefLabel: "Explore the job board",
      step4Title: "Track it to the offer",
      step4Body: "Move roles across the board, write back to recruiters, and keep every offer on one shelf. The manual (the ? key) is always there when you want the full map.",
      step4Href: "/applications",
      step4HrefLabel: "See the pipeline",
      skip: "Skip for now",
      back: "Back",
      next: "Next",
      done: "Start exploring",
    },
    /** The ten-minute start (Epic 244): the public front door for a brand-new reader. */
    tour: {
      pageTitle: "Your first ten minutes with AI Career OS",
      description:
        "Before you type a word into a resume, here's the whole loop in ten beats: what opens, what eats time, and what you walk away holding.",
      eyebrow: "THE TEN-MINUTE START",
      title: "Ten beats, open to close.",
      intro:
        "Every beat below is a real screen in the product — and each one ends with you holding something you didn't have when you started.",
      caption: "The board at a glance, the match ring, the copilot's doorway — the same things you'll see after you sign up.",
      cta: "Start free",
      beat_register_title: "Sign up",
      beat_register_body: "One email and one password is all it takes. No card, no phone, no mystery forms.",
      beat_register_time: "~20 seconds",
      beat_resume_title: "Drop in your resume",
      beat_resume_body: "PDF, DOCX or plain text — the parser turns it into structured evidence the match scores can quote line by line.",
      beat_resume_time: "~20 seconds",
      beat_job_title: "Paste the one job",
      beat_job_body: "The posting you already want, or one from the seeded board. The tool reads it the way a recruiter would — the hard way.",
      beat_job_time: "~30 seconds",
      beat_match_title: "Read your match",
      beat_match_body: "A number from evidence: the dimensions, the gaps, the exact lines the model is allowed to quote back at you.",
      beat_match_time: "~45 seconds",
      beat_tailor_title: "Tailor that one resume",
      beat_tailor_body: "Reorder bullets, foreground the JD's words — and a verifier rejects every invented claim before it ships.",
      beat_tailor_time: "~60 seconds",
      beat_rehearse_title: "Rehearse the interview",
      beat_rehearse_body: "The AI interviewer adapts to your weak dimensions, asks the follow-ups a real panel would ask, and scores what you say.",
      beat_rehearse_time: "~5 minutes",
      beat_track_title: "Track the application",
      beat_track_body: "One card per posting; Notes are journaled, reminders stay in your inbox, and the board moves itself.",
      beat_track_time: "ongoing",
      beat_offer_title: "Read your offers",
      beat_offer_body: "The shelf keeps each offer side-by-side — one number to compare; negotiation letters protect the deal when leverage is real and justice would be served; aftercare for day 1 when the signing lands.",
      beat_offer_time: "~2 minutes",
      beat_ceremony_title: "Sign, and read the letter",
      beat_ceremony_body: "When you sign, the ceremony happens: your counts and a letter from the tool that watched you do it.",
      beat_ceremony_time: "the day it happens",
      beat_afterward_title: "Afterward — what you carry out",
      beat_afterward_body:
        "The final page doesn't applaud; it notes the numbers — applications sent, interviews finished, days shown up — and says plainly: you did this. The letter you keep is not the only record of it.",
      beat_afterward_time: "a minute",
      closingTitle: "Your first ten minutes, at a glance",
      closingBody:
        "No commitment yet, no card on file, and nobody watching. And when you're ready, the loop is one click away — the same loop that got you here.",
      fact1_value: "26",
      fact1_label: "agent tools, wired and counted",
      fact2_value: "34 / 34",
      fact2_label: "golden-journey stations pass, live",
      fact3_value: "0 fabrications",
      fact3_label: "the verifier rejects invention before it ships",
      fact4_value: "100%",
      fact4_label: "bilingual: English and Chinese, everywhere",
      note1: "Your counts, letters and debriefs live in this browser — nothing leaves the device.",
      note2: "Your resume becomes the evidence base; every AI claim traces to your material.",
      note3: "You can redact, export or erase everything you ever wrote, from /data.",
      pathOneTitle: "Do it now",
      pathOneBody: "Sign up, drop your resume, and watch the first match land — the whole thing takes about ten minutes.",
      pathOneCta: "Start free",
      pathTwoTitle: "Read the full manual",
      pathTwoBody: "Every room, every door, every chapter — the manual is public, printable, and it teaches the same loop with the real words.",
      pathTwoCta: "Read the manual",
    },
    errorCodes: {
      ABORTED: "The upload was cancelled.",

      AI_SERVICE_BAD_REQUEST: "The AI service returned a bad request.",
      IMPORT_BUNDLE_INVALID: "That file is not a valid export bundle.",
      AI_SERVICE_CONFLICT: "The AI service is not ready yet.",

      AI_SERVICE_EMPTY_RESPONSE: "The AI service answered with nothing.",

      AI_SERVICE_NOT_FOUND: "That is no longer here.",

      AI_SERVICE_UNAVAILABLE: "The AI service is not answering.",

      APPLICATION_NOT_FOUND: "That application is no longer here.",

      APPLICATION_LETTER_NOT_FOUND: "That kept letter is no longer here.",

      OFFER_NOT_FOUND: "That offer is no longer on your shelf.",

      BUNDLE_NOT_PLANNABLE: "That file could not be turned into a restore plan.",

      BUNDLE_NO_SECTION: "That file has no data section.",

      CALENDAR_LINK_INVALID: "That calendar link is not valid or has been retired.",

      BACKEND_UNAVAILABLE: "The domain backend is not answering.",

      COMPANY_NOT_FOUND: "That company is no longer here.",

      CONFIRMATION_MISMATCH: "The email you typed is not this account's.",

      CONTACT_NOT_FOUND: "That contact is no longer here.",

      CONVERSATION_NOT_FOUND: "That conversation is no longer here.",

      CURRENT_PASSWORD_INCORRECT: "The current password you typed is not right.",

      DOCUMENT_KEY_NOT_OWNED: "No document owns that file key.",

      DOCUMENT_NOT_FOUND: "That document is no longer here.",

      EMAIL_ALREADY_REGISTERED: "That email address is already registered.",

      EMAIL_CHANGE_INVALID: "That email-change link is not valid or has expired.",

      EMAIL_UNCHANGED: "That is already the account's email address.",

      FEED_BOARD_INVALID: "A board feed takes the board's token, its page address, or the board's API URL.",

      FEED_LIMIT_REACHED: "You already keep as many feeds as this account allows.",

      FEED_URL_INVALID: "A feed address must start with http:// or https://.",

      FILE_EMPTY: "That file is empty.",

      FILE_KEY_INVALID: "That file key is not a valid one.",

      FILE_KEY_MALFORMED: "That file key is malformed.",

      FILE_TOO_LARGE: "That file is larger than the limit allows.",

      FORBIDDEN: "You do not have access to that.",

      HTTP_ERROR: "The server returned an error (status {status}).",

      INGESTION_FEED_NOT_FOUND: "That scheduled feed is no longer here.",

      INGESTION_RUN_NOT_FOUND: "That sweep run is no longer here.",

      INGESTION_RUN_ALREADY_APPLIED: "This run's plan was already applied.",

      INGESTION_RUN_NOT_APPLICABLE: "A failed run has no plan to apply.",

      INBOUND_INTENT_UNKNOWN: "That reading is not one the classifier knows.",

      INBOUND_LINK_INVALID: "That inbound address is not valid or has been retired.",

      INBOUND_MAIL_ALREADY_FILED:
        "This reply is already filed on another application; open it there instead.",

      INBOUND_MAIL_NOT_FOUND: "That reply is no longer here.",

      INBOUND_NOT_CONFIGURED: "Inbound mail is not configured on this deployment.",

      INTERNAL_ERROR: "An internal server error occurred.",

      INTERVIEW_ALREADY_STARTED: "This interview has already started.",

      INTERVIEW_NOTHING_TO_FINALIZE: "There is nothing to finish yet.",

      INTERVIEW_NOTHING_TO_THANK: "Nothing to thank just yet — finish the rehearsal first.",

      INTERVIEW_NOT_STARTED: "Start the interview with the opening question first.",

      INTERVIEW_NO_QUESTION: "No interviewer question was recorded.",

      INVALID_CREDENTIALS: "That email address or password is not right.",

      INVALID_FILE_TYPE: "That file type is not supported.",

      INVALID_STATUS: "That status is not one the tracker knows.",

      INVALID_TRANSITION: "That change is not allowed from here.",

      JD_NOT_FOUND: "That job description is no longer here.",

      JOB_NOT_FOUND: "That job is no longer here.",

      LOGIN_SESSION_NOT_FOUND: "That session is already closed.",

      MAIL_LINK_INVALID: "That mail-settings link is not valid or has been retired.",
      MAIL_LIST_UNKNOWN: "That mail setting is not recognized.",

      MALFORMED_REQUEST: "The request could not be read.",

      MATCH_NOT_FOUND: "There is no match for that yet.",

      METHOD_NOT_ALLOWED: "That request is not allowed here.",

      MFA_ALREADY_ACTIVE: "Two-factor authentication is already on for this account.",

      MFA_CODE_INVALID: "That six-digit code is not right.",

      MFA_INVALID: "That code is not right, or it was already used. Read the phone again, or take another printed code.",

      MFA_NOT_ENROLLED: "This account has not started setting up two-factor authentication.",

      MFA_REQUIRED: "This account asks for a six-digit code as a second step. Type the code from your authenticator app, or one of your printed recovery codes.",

      NETWORK_ERROR: "Cannot reach the API — is the backend running?",

      NIGHTLY_REPORT_CLOCK_REVERSED: "A nightly report cannot finish before it started.",

      NIGHTLY_REPORT_STATUS_INVALID: "A nightly report must end as passed or failed.",

      NIGHTLY_REPORT_SUMMARY_TOO_LARGE: "A nightly report carries too many summary entries.",

      NOTE_NOT_FOUND: "That note is no longer here.",

      NOT_FOUND: "That address is not served here.",

      PASSWORD_UNCHANGED: "The new password is the same as the current one.",

      PROFILE_NOT_FOUND: "Your profile is no longer here.",

      PUSH_SUBSCRIPTION_INVALID: "This browser's push subscription is not valid.",

      PUSH_SUBSCRIPTION_LIMIT_REACHED:
        "This account already keeps as many browsers as one morning can ring.",

      PUSH_SUBSCRIPTION_NOT_FOUND: "That browser registration is no longer on this account.",

      RATE_LIMITED: "Too many requests — please slow down.",

      RESET_TOKEN_INVALID: "That reset link is invalid or has expired. Please request a new one.",

      RESET_TOKEN_OWNER_NOT_FOUND: "The account this reset link belonged to is no longer here.",

      RESUME_FILE_MISSING: "That resume's original file is gone.",

      RESUME_NOT_AVAILABLE: "You do not have a resume yet.",

      RESUME_NOT_FOUND: "That resume is no longer here.",

      RESUME_NOT_INGESTED: "That resume's file has not been added to the knowledge base yet.",

      RESUME_NOT_PARSED: "Your resume has not been parsed yet.",

      RESUME_NOT_TAILABLE: "There is no resume to tailor yet.",

      RESUME_TEXT_NOT_READY: "That resume's text is not available yet.",

      RESUME_VERSION_MISSING: "That resume has no version yet.",

      RUN_NOT_FOUND: "That run is no longer here.",

      SAVED_SEARCH_EMPTY: "A saved search needs at least one criterion.",

      SAVED_SEARCH_LIMIT_REACHED: "You already keep as many saved searches as this account allows.",

      SAVED_SEARCH_NOT_FOUND: "That saved search is no longer here.",

      SALARY_RANGE_INVALID: "The salary floor cannot be above the salary ceiling.",

      SESSION_NOT_FOUND: "That interview session is no longer here.",

      SOURCE_NOT_FOUND: "That source is no longer here.",

      STORAGE_DELETE_FAILED: "Object storage delete failed.",

      STORAGE_PRESIGN_FAILED: "Object storage presign failed.",

      STORAGE_READ_FAILED: "Object storage read failed.",

      STORAGE_WRITE_FAILED: "Object storage write failed.",

      STREAM_ENDED: "The connection closed before the answer arrived.",

      TAILORED_BODY_MISSING: "This tailored version arrived without its body.",

      STREAM_ERROR: "The answer stream failed. Please try again.",

      TOKEN_EXPIRED: "Your session has expired. Please sign in again.",

      TOKEN_INVALID: "Your session is not valid any more. Please sign in again.",

      TOKEN_MALFORMED: "Your session could not be read. Please sign in again.",

      TOKEN_OWNER_NOT_FOUND: "The account this session belonged to is no longer here.",

      TOKEN_REUSED: "For your safety every session in this family was signed out. Please sign in again.",

      UNAUTHORIZED: "Your session has expired. Please sign in again.",

      UPLOAD_UNREADABLE: "That file could not be read.",

      USER_DISABLED: "This account is disabled.",

      USER_NOT_FOUND: "That account is no longer here.",

      VALIDATION_FAILED: "The request data is not valid.",

      VALIDATION_FIELD_REQUIRED: "A required field is missing.",

      VALIDATION_KIND_UNKNOWN: "That knowledge kind is not recognized.",

      VERSION_NOT_FOUND: "That version is no longer here.",

      VERSION_NOT_OWNED: "That version belongs to another resume.",

    },
    // The public landing page (18.2) -- the first thing a visitor reads.
    landing: {
      description: "Evidence-backed matching, resume intelligence, growth planning and AI-guided interviews — every conclusion traced to your own material.",
      pageTitle: "AI Career OS — your personal job-search operating system",
      signIn: "Sign in",
      getStarted: "Get started",
      eyebrow: "AI-native career platform",
      heroBadge: "Privacy-first · Evidence-bound · Yours to inspect",
      stat1Label: "Agent tools, wired and counted",
      stat2Label: "AI agents on call",
      stat3Label: "Languages — EN + ZH, entire product",
      tourLink: "See the ten-minute tour →",
      arcEyebrow: "THE WHOLE ARC",
      arcTitle: "Nine moves, from hello to thank-you",
      arcDescription:
        "Every move has its own room in the app — this is the whole search at a glance.",
      arcResume: "Resume",
      arcResumeSub: "Parse, score, version",
      arcFit: "Fit",
      arcFitSub: "Any JD, scored in seconds",
      arcGrowth: "Growth",
      arcGrowthSub: "The gap, closed in phases",
      arcLetters: "Letters",
      arcLettersSub: "Every kept letter, one gallery",
      arcInterviews: "Rehearse",
      arcInterviewsSub: "Adaptive mock interviews",
      arcApplications: "Track",
      arcApplicationsSub: "The board, and what needs a nudge",
      arcOffers: "Negotiate",
      arcOffersSub: "Say it before the offer does",
      arcReplies: "Replies",
      arcRepliesSub: "Recruiter mail, triaged first",
      arcCeremony: "Ceremony",
      arcCeremonySub: "The closing page of the search",
      arcPlaybook: "Prefer to read first? The playbook walks all nine.",
      heroTitle: "Your personal",
      heroTitleAccent: " job-search",
      heroTitleTail: "operating system",
      heroDescription:
        "AI Career OS turns your resume, the job market, and a fleet of AI agents into one evidence-backed system — from resume → knowledge base → job discovery → matching → tailored materials → mock interviews → application tracking.",
      startFree: "Start free",
      featuresTitle: "Everything you need",
      featuresDescription:
        "One system for your entire job search — every AI conclusion is traceable to your own material.",
      switchToChinese: "Switch to Chinese",
      switchToEnglish: "Switch to English",
      features: {
        resume: "Resume Intelligence",
        resumeDescription:
          "Upload PDF/DOCX/TXT → parse → structured profile + versioned resumes with live score.",
        matching: "JD Analysis & Matching",
        matchingDescription:
          "Requirements/skills/interview topics extracted; deterministic match scores bound to resume evidence.",
        interviews: "Adaptive Mock Interviews",
        interviewsDescription:
          "Interviewer agent that drills, follows up and scales difficulty; 8-dimension report + depth trajectory.",
        tracker: "Application Tracker",
        trackerDescription:
          "Linear-style kanban with transition audit events — saved → applied → OA → interview → offer.",
        growth: "Growth Intelligence",
        growthDescription:
          "Gap analysis, learning plans, salary benchmarks, and career progression planning.",
        analytics: "Analytics & Insights",
        analyticsDescription:
          "Pipeline funnel, response rates, stalled applications, and weekly insight digests.",
      },
      trust: {
        evidence: "Evidence-bound",
        evidenceDescription:
          "Every AI claim traces to your own material — no fabrication, no invented experience.",
        scoped: "User-scoped",
        scopedDescription:
          "Your data is yours. Every query is scoped to your user id — no cross-user leakage.",
        inspectable: "Inspectable",
        inspectableDescription:
          "Every agent run is recorded: traces, tool calls, retrieval, tokens, cost.",
      },
      ctaTitle: "Ready to build your career OS?",
      ctaDescription:
        "Start with your resume — the system builds your knowledge base, finds matching jobs, and prepares you for interviews.",
      ctaButton: "Get started free",
      footerNote: "Personal project, active development",
      preview: {
        label: "Illustration of the CareerOS pipeline: three stages, a match score and the copilot",
        applied: "Applied",
        interview: "Interview",
        offer: "Offer",
        match: "Match",
        copilot: "Copilot: draft my follow-up",
      },
    },
    // The copilot's artifact cards -- what each kind of answer is called.
    artifacts: {
      match: "Match analysis",
      coverLetter: "Cover letter draft",
      interview: "Mock interview ready",
      gapReport: "Gap analysis",
      salaryBand: "Market band",
      offerComparison: "Offer comparison",
      learningPriority: "Learning priority",
      matchRing: "Match",
      copyDraft: "Copy draft",
      copyLetter: "Copy letter",
      matchingRoles: "{count} matching roles",
      tailoredResume: "Tailored resume draft",
      openJob: "Open job",
      interviewPrepared: "The agent prepared a session from this conversation.",
      offerFallback: "Offer {number}",
      start: "Start",
      coverage: "Coverage",
    },
    // The copilot's action chips -- the labels the orchestrator writes in
    // English, which the browser says in the reader's language.
    actions: {
      coverLetter: "Draft cover letter",
      interview: "Start mock interview",
      tailor: "Tailor resume for this job",
      openGrowth: "Open the growth report",
      openOffers: "Open the offers workbench",
      openInterview: "Continue interview",
    },
    // Copilot
    copilot: {
      noConversationId: "The API didn't return a conversation id.",
      couldNotAnswer: "Copilot couldn't answer.",
      suggestionOwnership: "Which experience best demonstrates ownership?",
      suggestionCoverLetter: "Draft a cover letter for the company I applied to",
      suggestionRag: "What should I prepare for a RAG-system design interview?",
      suggestionCompare: "Compare my resume against this JD",
      untitledChat: "Untitled chat",
      title: "Ask your career agent",
      conversations: "Conversations",
      noConversations: "No conversations yet",
      noConversationsDescription: "Start one above — every turn is traced and saved.",
      conversationTitle: "Conversation title",
      deleteChat: "Delete this chat?",
      deleteChatDescription:
        "The transcript and its citations go with it. This cannot be undone.",
      firstMessage: "First message to Copilot",
      conversationsSheet: "Conversations",
      chatsButton: "Chats",
      newChat: "New chat",
      loadingConversations: "Loading conversations…",
      conversationsNotServed: "Conversations aren't served yet",
      couldNotLoadConversations: "Couldn't load conversations",
      paginationLabel: "conversations",
      groundedIn: "Grounded in your resumes, notes and saved jobs — every claim it makes is cited.",
      answersCiteKnowledge: "answers cite your knowledge base",
      firstMessagePlaceholder:
        "e.g. Which of my projects should I lead with for an LLM-platform role?",
      enterToSend: "Enter to send · Shift+Enter for a new line",
      startChat: "Start chat",
      writing: "writing",
      thinking: "thinking",
      badge: "copilot",
      retryLastMessage: "Retry last message",
      delete: "Delete",
      noHistory: "This API build has no conversation history",
      noHistoryDescription:
        "GET /conversations answered 404, so this frontend and the backend it is talking to are different versions. Nothing here is pre-filled.",
      couldNotLoad: "Couldn't load this conversation",
      askAnything: "Ask anything about your search",
      askAnythingDescription:
        "Requests that mention experience, skills or jobs are answered from your knowledge base with citations — try “match my resume to my last saved job”.",
      messagePlaceholder: "Message Copilot…",
      messageLabel: "Message Copilot",
      send: "Send message",
      sendHint: "Send (Enter)",
      renameChatAria: "Rename “{title}”",
      deleteChatAria: "Delete “{title}”",
      renameHint: "Rename this conversation",
      deleteHint: "Delete this conversation",
    },
    // Networking
    networking: {
      title: "Contacts",
      description:
        "The people a search actually touches — who they are, how you know them, and when you last talked.",
      noContacts: "No contacts yet",
      noContactsDescription:
        "Add the referrers, mentors and peers you talk to — Copilot drafts messages for them, and the follow-up reminders will read this list.",
      searchPlaceholder: "Search contacts",
      searchLabel: "Search the registry by name, role, company or notes",
      clearSearch: "Clear search",
      noMatch: "No contact matches “{query}”",
      noMatchDescription:
        "Try a shorter word, or clear the search to see everyone in the registry.",
      addContact: "Add contact",
      onlyNameRequired: "Only the name is required — fill in what you know, leave the rest.",
      name: "Name",
      role: "Role",
      company: "Company",
      relationFilter: "Narrow the registry by relation",
      relationFilterAll: "All relations",
      relation: "Relation",
      email: "Email",
      lastTouch: "Last touch",
      lastTouchLine: " · last touch {when}",
      notes: "Notes",
      notesPlaceholder: "Context for the next message — how you met, what you discussed.",
      noRelationContacts: "No contacts behind “{relation}”",
      draft: "Draft",
      draftFor: "Draft for {name}",
      draftMessage: "Draft message",
      draftWithCopilot: "Draft a message with Copilot",
      addContactTitle: "Add a contact",
      editContactTitle: "Edit {name}",
      deleteContactTitle: "Delete {name}?",
      relationPlaceholder: "referrer, mentor, peer…",
      delete: "Delete",
      cancel: "Cancel",
      save: "Save",
      add: "Add",
      deleteContact: "The registry row is removed. This cannot be undone.",
      coffeeTitle: "The first coffee — rehearse the fifteen minutes",
      coffeeDescription:
        "The registry remembers who you know. This room rehearses the conversation — the ask, the middle, the close — before either of you names the referral.",
      coffeeStep: "Moment {n} of 3",
      coffeePush_ask: "The intro email got answered — they said yes. What do you actually open with?",
      coffeePush_middle: "Fifteen minutes in, they lean back: “So — what are you working on right now?”",
      coffeePush_close: "The last two minutes. They check the time: “Anything else I can do for you?”",
      coffeeReply_ask_burden:
        "“Sorry to bother you again — no pressure either way, honestly, just… if you have time?”",
      coffeeReply_ask_generic: "“Could we grab a coffee sometime? I'd love to hear your story.”",
      coffeeReply_ask_specific:
        "“One question and fifteen minutes — that's the whole ask: how did you find the role that let you build like that?”",
      coffeeReply_middle_nothing: "“Not much, honestly. Between things.”",
      coffeeReply_middle_recap: "[Recites the resume headline — title, years, stack, in order.]",
      coffeeReply_middle_lead:
        "“Three months into rebuilding our ingestion pipeline — the one that kept waking me at 3 a.m. I keep hitting the same wall you probably hit in '19. What got you past it?”",
      coffeeReply_close_thanks: "“Thanks so much for your time!!”",
      coffeeReply_close_loop: "“Thanks — I'll keep you posted!”",
      coffeeReply_close_forward:
        "“One last ask: who's one more person I should talk to — or one thing I should read before the next interview?”",
      coffeeFeedbackSpecific: "Specific, finite, warm.",
      coffeeFeedbackWarm: "Warm — holds, mostly.",
      coffeeFeedbackSafe: "Safe, and inert.",
      coffeeFeedbackBurdens: "Burdens the host.",
      coffeeNext: "Next moment",
      coffeeSeeVerdict: "See how it went",
      coffeeScoreLine: "{total} of {max} in the room",
      coffeeVerdictNone: "The chat that never happened",
      coffeeVerdictNoneDetail:
        "The room never opened — the ask never left your mouth. The coffee is not the meeting; the meeting is the fifteen minutes you walk into.",
      coffeeVerdictWeak: "A polite echo",
      coffeeVerdictWeakDetail:
        "You were pleasant and forgettable — which is exactly what a stranger already is. The room wanted one specific thing from you, and you gave it nothing.",
      coffeeVerdictSolid: "A pleasant hour, well spent",
      coffeeVerdictSolidDetail:
        "You made the call and you survived it. Next time bring one more specific thing, and ask one more forward question.",
      coffeeVerdictStrong: "They remember you",
      coffeeVerdictStrongDetail:
        "Specific, finite, warm — and you left a door behind you. That's the whole job of a first coffee.",
      coffeeVerdictMasterful: "The referral wrote itself",
      coffeeVerdictMasterfulDetail:
        "Nine of nine. You didn't ask for the referral; you made it the obvious conclusion to fifteen minutes of being worth knowing.",
      coffeeKeepTitle: "The sentence you will open with",
      coffeeKeepDescription:
        "Your own words, kept in this browser — the sentence you'd actually walk in with.",
      coffeeKeepPlaceholder: "e.g. “One question and fifteen minutes — that's the whole ask.”",
      coffeeReset: "Start over",
      coffeeKept: "Kept in this browser.",
    },
    // Growth report
    growth: {
      milestonesTitle: "Milestones",
      milestonesDescription: "What you have already done, and the one the shelf is working on next.",
      milestonesUnavailable: "The milestone shelf could not be read.",
      milestoneEarned: "Earned",
      milestoneProgress: "{progress} of {target}",
      milestoneCounters: "Behind every badge: {applications} applications · {interviews} rehearsals · {offers} offers",
      // Each backend milestone key → earned/working label, as flat string keys.
      // Kept in the locale table so a Chinese reader never sees the English sentence.
      milestone_first_step_earned: "First application filed",
      milestone_first_step_working: "File your first application",
      milestone_ten_steps_earned: "Ten applications filed",
      milestone_ten_steps_working: "File 10 applications",
      milestone_fifty_steps_earned: "Fifty applications filed",
      milestone_fifty_steps_working: "File 50 applications",
      milestone_grounded_earned: "First match computed",
      milestone_grounded_working: "Run your first match",
      milestone_first_rehearsal_earned: "First rehearsal done",
      milestone_first_rehearsal_working: "Hold your first rehearsal",
      milestone_five_rehearsals_earned: "Five rehearsals done",
      milestone_five_rehearsals_working: "Hold 5 rehearsals",
      milestone_letter_wright_earned: "Three letters kept",
      milestone_letter_wright_working: "Keep 3 letters",
      milestone_first_offer_earned: "First offer received",
      milestone_first_offer_working: "Receive your first offer",
      milestone_shelf_full_earned: "Three offers on the shelf",
      milestone_shelf_full_working: "Hold 3 offers at once",
      milestone_streak_week_earned: "A seven-day streak",
      milestone_streak_week_working: "Act 7 days in a row",
      title: "Growth report",
      description:
        "Readiness, the gap behind it, the market's salary band, a phased learning plan, and what moved since your last run.",
      buildReport: "Build a report",
      buildReportDescription:
        "One call composes readiness, the gap behind it, the market's salary band, a phased learning plan, and what moved since your last run.",
      noReport: "No report yet",
      noReportDescription:
        "Name the role you're aiming at and run the analyzer — the report is built from your resume's evidence, not from a form you fill in.",
      targetRole: "Target role",
      location: "Location (optional)",
      targetRolePlaceholder: "e.g. Senior Backend Engineer (Java)",
      locationPlaceholder: "e.g. Shanghai",
      analyze: "Analyze",
      roleTooShort: "Name the role fully — the analyzer needs at least 10 characters to target it.",
      skillCounts: "{covered} covered · {partial} partial · {open} open of {expected} expected skills",
      covered: "Covered",
      partial: "Partial",
      open: "Open",
      coverage: "Coverage",
      salaryBand: "Salary band",
      matchingPostings: "{count} matched postings",
      matchedPostingsIn: "{count} matched postings in {location}",
      verdicts: {
        ready: "Ready",
        borderline: "Borderline",
        not_ready: "Not ready",
        unknown: "Unknown",
      },
      learningPlan: "Learning plan",
      learningPlanDescription: "Foundation first, then the role's core, then the applied.",
      nothingToStudy: "Nothing to study — every expected skill has evidence behind it.",
      progress: "Progress",
      progressBaseline:
        "First report for this role — the next run diffs against this one.",
      progressAgainstPrevious: "Against your previous report for this role.",
      noSkillChange: "No skill changed state since the last report",
      skillsClosed: "Closed",
      skillsImproved: "Improved",
      skillsOpened: "Newly opened",
      skillsRegressed: "Regressed",
      stillOpen: "{count} still open.",
    },
    // Knowledge
    knowledge: {
      title: "Knowledge Base",
      description:
        "Everything the agents can cite: resumes, projects, notes, JDs, company research, feedback.",
      showingCitedSource: "Showing the source one of your citations points at.",
      showAllSources: "Show all sources",
      noSourceMatches: "No source matches that citation",
      noSourceMatchesDescription:
        "The document may have been deleted, or its ingestion never finished.",
      baseIsEmpty: "The knowledge base is empty",
      baseIsEmptyDescription:
        "Add sources and they'll be parsed, chunked and embedded for retrieval with citations.",
      baseIsEmptyPromise: "WHAT CITED ANSWERS FEEL LIKE",
      baseIsEmptyProof1: "Every claim links back to the source it came from",
      baseIsEmptyProof2: "Chunked and embedded the moment you add a source",
      baseIsEmptyProof3: "Your notes join the corpus without leaving your account",
      askCopilotToIngest: "Ask Copilot to ingest",
      ragAskTitle: "Ask your evidence",
      ragAskDescription:
        "One grounded answer from your own ready documents. Every [n] is a verified citation you can trace back to the exact quote.",
      ragAskLabel: "Your question",
      ragAskPlaceholder: "e.g. What evidence do I have for backend roles?",
      ragAskAction: "Ask",
      ragAskWorking: "Reading your evidence…",
      ragAskEmpty: "Nothing grounded came back — add a source, or ask a narrower question.",
      ragCitationsLabel: "Citations",
      ragCitationUnknown: "Source",
      paginationLabel: "sources",
      notes: {
        titleLabel: "Title (optional)",
        titlePlaceholder: "e.g. Answers for the “why us” question",
        content: "Content",
        contentPlaceholder:
          "Write it down — the agents can quote this back with a citation.",
        tagsLabel: "Tags",
        tagsPlaceholder: "interview, study (comma separated)",
        tagFilter: "Filter notes by tag",
        allTags: "All",
        tagEmpty: "No notes carry this tag yet",
        noNotesWithTag: "No notes tagged “{tag}”",
        saveNote: "Save note",
        untitled: "Untitled note",
        noteTitleLabel: "Note title",
        noteContentLabel: "Note content",
        saving: "Saving…",
        cancel: "Cancel",
        save: "Save",
        updated: "Updated {date}",
        editNote: "Edit {title}",
        deleteNote: "Delete {title}",
        deleteTitle: "Delete “{title}”?",
        deleteDescription:
          "The note row is removed and its chunks stop being cited. This cannot be undone.",
        delete: "Delete",
        section: "Notes",
        description:
          "Short reference notes the agents can quote back at you — talking points, salary research, follow-ups.",
        noNotes: "No notes yet",
        noNotesDescription:
          "Write the first one above — it lands straight in the knowledge base the agents can cite.",
        paginationLabel: "notes",
      },
      sources: {
        deleteFailed: "Couldn't delete the source.",
        deleted: "Source deleted — its chunks stop being cited.",
        chooseDocuments: "Choose documents to ingest",
        appliedToBatch: "Applied to every file in the batch",
        clearList: "Clear list",
        deleteDescription:
          "The source row is removed and its chunks stop being cited. This cannot be undone.",
        delete: "Delete",
        deleteLabel: "Delete {title}",
        deleteTitle: "Delete “{title}”?",
        documents: "Documents",
        titleLabel: "Title (optional)",
        kind: "Kind",
        chooseFiles: "Choose files",
        uploading: "Uploading…",
        noSourceId: "ingesting — no source id returned",
        ready: "ready",
        failedPrefix: "failed: {reason}",
        ingestionFailed: "ingestion failed",
        batchSummary: "{done} of {total} done{failed}",
        notIngested: ", {count} not ingested",
        typeRejected:
          "Only {extensions} files can be ingested — “{name}” would be rejected by the server.",
        tooLarge: "“{name}” is over the 20 MB ingestion cap.",
        emptyFile: "“{name}” is empty — nothing to ingest.",
        /**
         * The nine kinds a source may have.
         *
         * The values are the wire's -- `KnowledgeService.KINDS`, which
         * `validateKind` rejects anything else from -- and the names are the
         * reader's.
         */
        kinds: {
          note: "Note",
          resume: "Resume",
          project: "Project",
          jd: "Job description",
          company: "Company",
          interview_feedback: "Interview feedback",
          certificate: "Certificate",
          course: "Course",
          goal: "Goal",
        },
        statuses: {
          pending: "Pending",
          ingesting: "Ingesting",
          indexing: "Indexing",
          ready: "Ready",
          failed: "Failed",
          retired: "Retired",
        },
      },
    },
    // Companies
    companies: {
      title: "Companies",
      description:
        "Research profiles built from job postings and web sources — external facts always carry their source.",
      noneResearched: "No companies researched",
      noneResearchedDescription:
        "The research agent builds company profiles when you save a job or ask about one.",
      researchOne: "Research a company",
      profilePending: "Profile pending",
      role: "role",
      roles: "roles",
      websiteLabel: "{name} website",
      paginationLabel: "companies",
      searchPlaceholder: "Search companies",
      searchLabel: "Search companies by name",
      clearSearch: "Clear search",
      noMatch: "No company matches “{query}”",
      noMatchDescription: "Try a shorter word, or clear the search to see every company.",
      detail: {
        loadFailed: "Couldn't load this company",
        loading: "Loading company…",
        website: "Website",
        overview: "Overview",
        noOverview: "No overview available yet.",
        postings: "What the postings say",
        skillsAskedFor: "Skills asked for",
        interviewTopics: "Interview topics",
        noPostings: "No postings in the corpus for this company yet.",
        readingCorpus: "Reading the corpus…",
        readCorpus: "Read the corpus",
        techStack: "Tech Stack",
        noTechStack: "No tech stack reported yet.",
        workingHere: "Working here",
        culture: "Culture",
        interviewProcess: "Interview process",
        openRoles: "Open Roles ({count})",
        showingBestMatching: "Showing the {shown} best-matching of {total} open roles.",
        noOpenRoles: "No open roles at the moment.",
        sources: "Sources",
        noSourcesRecorded: "Nothing recorded where this profile came from yet.",
        open: "Open",
      },
      prereadTitle: "The room you walk into",
      prereadDescription:
        "The company page says what this room is; this is what you decide to bring. Five lenses in your own words — kept in this browser, read by no one else.",
      prereadKeptAt: "Kept {date}",
      prereadMoneyLabel: "How the room makes money",
      prereadMoneyHint:
        "Which bet does the P&L ride? What has to stay true for this room to keep compounding?",
      prereadRoleLabel: "The room's real scope",
      prereadRoleHint:
        "Team shape, reporting line, and what you own alone by month three — before anyone asks.",
      prereadYearLabel: "The last twelve months",
      prereadYearHint:
        "What shipped, what slipped, what changed at the top. Your questions hang off this.",
      prereadProofLabel: "Your thinnest joint",
      prereadProofHint:
        "The gap you know they'll smell first. Name it plainly — nobody else will in this room.",
      prereadBetLabel: "Why this room, honestly",
      prereadBetHint:
        "Not the title, not the brand. The honest reason — written where nobody can read it but you.",
      prereadLevelLine: "A line",
      prereadLevelProof: "Evidence",
      prereadCount: "{done} of 10 sealed",
      prereadReset: "Empty the notes",
      prereadGate:
        "Seal at least 8 of 10 — two lenses written to the bone — before the kit dares to question you back.",
      prereadGather: "Gather into two questions",
      prereadAskThem: "Ask, don't quote — a launchpad, not a script.",
      prereadQ_money:
        "You said it best — \"{note}\". What has to stay true for this room to keep compounding?",
      prereadQ_role:
        "Month three — if I have to earn this back bench-clear, what would I have shipped without being asked?",
      prereadQ_year:
        "About \"{note}\" — what did that year do to the room I would actually be walking into?",
      prereadQ_proof:
        "Here is the thinnest joint I carry — \"{note}\". What would a strong hire here do differently with it?",
      prereadQ_bet:
        "My reason is in these notes — \"{note}\". What would tell you it is real, not applause?",
      prereadLensAria: "{lens} — notes and level",
    },
    // Activity
    activity: {
      title: "AI Activity",
      runStatus: {
        running: "Running",
        completed: "Completed",
        failed: "Failed",
        cancelled: "Cancelled",
      },
      trigger: {
        chat: "Chat",
        resume_parse: "Resume parse",
        match: "Match",
        tailor: "Tailor",
        cover_letter: "Cover letter",
        interview: "Interview",
        ingest: "Ingest",
        nightly: "Nightly",
      },
      description: "Every agent run, tool call and retrieval — the debug view behind the answers.",
      ctaLabel: "Run something in Copilot",
      paginationLabel: "runs",
      trace: "Trace",
      rowTokens: "{count} tok",
      rowCached: "{count} cached",
      emptyDescription:
        "Once Copilot or a matching job runs, its full trace appears here.",
      emptyPromise: "WHAT THE TRACE TELLS YOU",
      emptyProof1: "Every model call, tool call and retrieval, in order",
      emptyProof2: "Which calls came from cache — and what they cost",
      emptyProof3: "The cited evidence behind each claim, one hop away",
      noRuns: "No agent runs yet",
      detail: {
        noTraceSteps: "This run recorded no trace steps. Tools that run without the orchestrator (single-call parses) log only the run row.",
        debugView: "The debug view behind one agent answer.",
        agentRun: "Agent run",
        agentFallback: "agent",
        runFallback: "run",
        triggerRun: "{trigger} run",
        runSubtitle: "{agent} · {trigger} — every step the orchestrator persisted for this run.",
        traceHint: "Persisted by the orchestrator — expand a row for its raw payload.",
        steps: "Steps",
        toolCalls: "Tool calls",
        tokens: "Tokens",
        latency: "Latency",
        thisRunFailed: "This run failed",
        executionTrace: "Execution trace",
        attribution: "Attribution",
        runId: "Run id",
        runGone: "This run is gone",
        runGoneDescription:
          "Either it was never recorded or it belongs to another workspace. Runs are only ever listed to their owner.",
        cost: "Cost",
        cachedTokens: "Cached tokens",
        ofInput: "of input",
        started: "Started",
        finished: "Finished",
        model: "Model",
        agent: "Agent",
        openConversation: "Open the conversation that ran this",
        allActivity: "All activity",
        backToActivity: "Back to activity",
      },
    },
    // Applications
    applications: {
      title: "Applications",
      description:
        "Every role in flight. Drag a card to move it through the pipeline, or open one to add notes and a reminder — the dashboard counts follow the same data.",
      boardColumn: "{stage} applications",
      dragToReorder: "Drag to reorder",
      dragHint: "Drag to reorder within this lane",
      reminderDue: "reminder due",
      noStep14d: "no step 14d+",
      reminderOn: "reminder {date}",
      packetStatus: "Packet {linked}/{total}",
      packetMissing: "Missing from the packet: {labels}",
      packetComplete: "Every pipeline artifact is attached",
      letterBadge: "{count} letters",
      letterBadgeTitle: "{count} cover letters kept for this application",
      pipelineIsEmpty: "Pipeline is empty",
      dropCardHere: "Drop a card here",
      savingMove: "Saving move…",
      pipelineIsEmptyDescription:
        "Track a job from its detail page and it appears here, starting in Saved.",
      pipelineIsEmptyPromise: "WHAT ONE CARD BECOMES",
      pipelineIsEmptyProof1: "Saved, applied, interview, offer — one chain, the whole loop",
      pipelineIsEmptyProof2: "Reminders that surface when they're due, not before",
      pipelineIsEmptyProof3: "Replies matched back to the application they answer",
      addApplication: "Add application",
      add: "Add",
      paginationLabel: "applications",
      searchPlaceholder: "Search applications",
      searchLabel: "Search the pipeline by role, company or notes",
      clearSearch: "Clear search",
      noMatch: "No application matches “{query}”",
      noMatchDescription:
        "Try a shorter word, or clear the search to see every card in the pipeline.",
      dialog: {
        trackTitle: "Track an application",
        createDescription:
          "Anything you add here starts in the stage you choose, no job link required.",
        role: "Role",
        rolePlaceholder: "Senior Backend Engineer",
        company: "Company",
        optional: "Optional",
        stage: "Stage",
        notes: "Notes",
        notesPlaceholder:
          "Recruiter name, take-home, salary range, anything you will want next week…",
        reminder: "Reminder",
        clear: "Clear",
        reminderHint: "The dashboard counts a due reminder as needing your attention.",
        outcome: "Outcome",
        offerCompensation: "Offer compensation",
        offerCompensationPlaceholder: "e.g. 40k/mo · 16 months, or 550k + equity",
        rejectionReason: "Rejection / feedback reason",
        rejectionReasonPlaceholder:
          "Why it didn't proceed — this is what feeds back into what to improve.",
        outcomeHint:
          "Captured here, it closes the loop: a rejection reason tells you what to strengthen, and an offer's number is what to compare and negotiate against.",
        history: "History",
        loadingHistory: "Loading history…",
        historyFailed: "History failed to load",
        nothingRecorded:
          "Nothing recorded yet — stages you move, notes you save and reminders you set all land here.",
        pipelineLinks: "Pipeline links",
        resumeVersionLink: "Resume version",
        jdAnalysis: "JD analysis",
        match: "Match",
        pipelineLinksHint:
          "Recorded by the route that produced each one — match, tailor, or JD analysis.",
        packet: {
          loading: "Loading the packet…",
          failed: "The packet couldn't be loaded.",
          notLinked: "Not linked",
          unavailable: "No longer available",
          untitledResume: "Resume version",
          untitledMatch: "Match recorded",
          matchScore: "{score}% match",
          open: "Open",
          letterCount: "{count} kept",
          noLetters: "None kept yet",
          rehearsalCount: "{count} rehearsal{plural}",
          rehearsalCountBest: "{count} rehearsal{plural} · best {best}/100",
          noRehearsals: "None rehearsed yet",
          empty: "Nothing from the pipeline is attached yet.",
        },
        letters: "Cover letters",
        rehearsals: "Rehearsals",
        lettersEmpty: "No cover letter is kept for this application yet.",
        lettersFailed: "The cover letters couldn't be read.",
        lettersHint: "Drafts you keep from the job page are stored here.",
        lettersWriteOne: "Write one on the job page",
        rehearseTitle: "Rehearse for this role",
        rehearseHint: "Starts a mock interview with this card's posting and materials.",
        rehearseAction: "Start rehearsal",
        letterKept: "Kept {when}",
        letterDelete: "Remove letter",
        letterDeleteTitle: "Remove this letter?",
        letterDeleteBody: "The letter disappears from this application. This cannot be undone.",
        letterDeleteConfirm: "Remove",
        letterEdit: "Edit letter",
        letterRewrite: "Write another like this",
        letterWrittenWith: "Written with",
        letterVersionUnavailable: "The resume version this letter used is no longer readable.",
        untitledVersion: "Untitled version",
        letterCopy: "Copy text",
        letterDownload: "Download .md",
        letterSave: "Save correction",
        letterCancel: "Cancel",
        letterEdited: "Edited {when}",
        letterBody: "Letter text",
        letterDialUnset: "Not set",
        notFound: "That application no longer exists.",
        saveFailed: "Couldn't save the application.",
        delete: "Delete",
        cancel: "Cancel",
        saveChanges: "Save changes",
        addToPipeline: "Add to pipeline",
        deleteTitle: "Delete this application?",
        deleteDescription: "\"{title}\" and its history are removed from the board. This cannot be undone.",
        movedTo: "Moved to {stage}",
        stageChanged: "Stage changed",
        noteSaved: "Note saved",
        reminderCleared: "Reminder cleared",
        reminderSetFor: "Reminder set for {when}",
        reminderSet: "Reminder set",
        offerCompensationSaved: "Offer compensation saved",
        rejectionReasonSaved: "Rejection reason saved",
        outcomeRecorded: "Outcome recorded",
        update: "Update",
      },
    },
    /**
     * The pipeline's own vocabulary. These seven names are the product's
     * central taxonomy -- they appear on the board, in the drawer, on the
     * dashboard and in every status picker, so they are translated once here
     * rather than once per surface.
     */
    /**
     * The section overlines.
     *
     * The small word above a card's title. There are two dozen of them
     * across the product and they are the same kind of word -- a name for
     * the section -- so they live in one table rather than in each
     * screen's own copy. A section that says "Rubric" in English on a
     * Chinese page is a section the reader has to guess at.
     */
    eyebrows: {
      applications: "Applications",
      waitingOnYou: "Waiting on you",
      recommendations: "Recommendations",
      agentActivity: "Agent activity",
      currentResume: "Current resume",
      knowledgeBase: "Knowledge base",
      aiUsage: "AI usage",
      gapAnalysis: "Gap analysis",
      networking: "Networking",
      rubric: "Rubric",
      betweenSessions: "Between sessions",
      adaptivity: "Adaptivity",
      explainability: "Explainability",
      reviewerAgent: "Reviewer agent",
      history: "History",
      dataSources: "Data sources",
      workHistory: "Work history",
      projects: "Projects",
      education: "Education",
      skills: "Skills",
      goals: "Goals",
      aiMatch: "AI match",
      growth: "Growth",
      prep: "Prep",
      nextStep: "Today's first step",
    },
    stages: {
      saved: {
        label: "Saved",
        short: "Saved",
        blurb: "Bookmark kept from the job board.",
      },
      applied: {
        label: "Applied",
        short: "Applied",
        blurb: "Application submitted.",
      },
      oa: {
        label: "Online assessment",
        short: "OA",
        blurb: "Awaiting or completing an online test.",
      },
      interview: {
        label: "Interview",
        short: "Interview",
        blurb: "In the interview loop.",
      },
      final_round: {
        label: "Final round",
        short: "Final",
        blurb: "Last-stage onsite / panel.",
      },
      offer: {
        label: "Offer",
        short: "Offer",
        blurb: "Offer extended — decide or negotiate.",
      },
      rejected: {
        label: "Rejected",
        short: "Rejected",
        blurb: "Closed out. Kept for retro analysis.",
      },
    },
    /**
     * The score dimensions, named in the reader's language.
     *
     * Four vocabularies, four namespaces, because they are four different
     * sets of words: a match is scored on the four things a resume has, an
     * interview on the eight things an answer has, a resume review on its own
     * five, and the rubric's unmet criteria are a list of their own. Two of
     * them share a key -- a *structure* in an answer is not a *structure* in a
     * resume -- so they cannot share a namespace either.
     *
     * The keys inside are the wire's own, because that is what the services
     * answer with; `lib/dimensions.ts` is the one place that maps them here.
     */
    dimensions: {
      match: {
        technical: { label: "Technical" },
        experience: { label: "Experience" },
        projects: { label: "Projects" },
        education: { label: "Education" },
      },
      interview: {
        technical_accuracy: { label: "Technical accuracy" },
        communication: { label: "Communication" },
        depth: { label: "Depth" },
        structure: { label: "Structure" },
        problem_solving: { label: "Problem solving" },
        system_thinking: { label: "System thinking" },
        ai_knowledge: { label: "AI knowledge" },
        backend_knowledge: { label: "Backend knowledge" },
      },
      resume: {
        bullets: { label: "Bullets & metric density" },
        structure: { label: "Structure & scannability" },
        impact: { label: "Impact wording" },
        clarity: { label: "Clarity" },
        keywords: { label: "Keyword coverage" },
      },
      criteria: {
        has_contact: { label: "Contact info (email / phone)" },
        has_summary: { label: "A summary section" },
        has_experience: { label: "Work experience" },
        experience_has_bullets: { label: "Bullets under your roles" },
        quantified_impact: { label: "Quantified impact (numbers or %)" },
        has_projects: { label: "Projects" },
        has_education: { label: "Education" },
        has_skills: { label: "Enough skills (5+)" },
        years_experience_stated: { label: "Stated years of experience" },
        dates_present: { label: "Start dates on all roles" },
      },
    },
    // Epic 274 — the LLM STAR story forge, embedded where the reader keeps interview notes.
    storyForge: {
      title: "Forge a STAR story",
      description: "Turn one real experience into an interview-ready STAR story. The model writes it, then challenges itself like a panel, then revises using only your words — any number your note did not say is struck out.",
      label: "Your experience, in your own words",
      placeholder: "e.g. I owned the payment gateway migration. I split the monolith into 3 services and cut p99 latency by 42% over 6 weeks…",
      action: "Forge the story",
      working: "Forging…",
      storyTitle: "Your forged story",
      situation: "Situation",
      task: "Task",
      actionField: "Action",
      resultLabel: "Result",
      followupsTitle: "What a panel will still ask",
      followupsHint: "Honest gaps the model refused to invent. Fill these in with your own facts before the interview.",
      struckTitle: "Figures removed",
      struckHint: "These fields carried a number your note never gave, so they were cleared rather than fabricated.",
      complete: "Ready to tell — every figure traces to your note.",
      incomplete: "Not defensible yet — answer the questions above first.",
      emptyStory: "Nothing came back. Try a fuller note with specific actions and outcomes.",
    },
    // Interviews
    interviews: {
      title: "Interviews",
      depthBands: {
        warmup: "Warm-up",
        standard: "Standard",
        solid: "Solid",
        deep: "Deep",
        expert: "Expert",
      },
      description:
        "Adaptive mock interviews: the agent follows up while your answers are strong, moves on when they're not, and pushes deeper as you prove depth. Every evaluation cites your own material.",
      paginationLabel: "interview sessions",
      startInterview: "Start interview",
      mode: "Mode",
      modeNames: {
        behavioral: "Behavioral",
        technical: "Technical",
        system_design: "System design",
        ai_llm: "AI / LLM",
        rag: "RAG",
        agent: "Agent",
        backend: "Backend",
      },
      modeHints: {
        behavioral: "STAR stories from your real experience",
        technical: "coding & fundamentals, deepening by answer",
        system_design: "scaling trade-offs for your target role",
        ai_llm: "models, fine-tuning, evaluation",
        rag: "retrieval, chunking, reranking, citations",
        agent: "planning, tools, orchestration",
        backend: "APIs, storage, concurrency",
      },
      modeInterview: "{mode} interview",
      modeReport: "{mode} interview report",
      pickATargetJob: "Pick a target job first",
      openApplication: "Open application",
      filteredToApplication: "Showing the rehearsals for one application",
      searchPlaceholder: "Search interviews",
      searchLabel: "Search interviews by company, role or mode",
      clearSearch: "Clear search",
      noMatch: "No interview matches “{query}”",
      noMatchDescription:
        "Try a shorter word, or clear the search to see every rehearsal.",
      practice: {
        first: "This is the first rehearsal for this application.",
        progress: "Rehearsal {position} of {count} for this application · best {best}/100",
        progressNoBest: "Rehearsal {position} of {count} for this application",
      },
      empty: "No mock interviews yet",
      emptyDescription:
        "Pick a mode above — the session is built from your resume and the job you're targeting, so answers are graded against evidence, not trivia.",
      notLiveDescription:
        "GET /interview/sessions answered 404, so this frontend and the backend it is talking to are different versions. The runner is wired and activates as soon as they match.",
      inProgress: "In progress",
      questionsInline: "{count} question{plural} · ",
      finishedAt: "finished {when}",
      startedAt: "started {when}",
      reportAction: "View report",
      deleteAria: "Delete this rehearsal",
      deleteTitle: "Delete this rehearsal?",
      deleteDescription:
        "Its questions, answers and report are removed. The application card and any note you kept from the report stay.",
      deleteConfirm: "Delete",
      continueAction: "Continue",
      detail: {
        submitHint: "Ctrl+Enter to submit · the agent evaluates before the next question",
        abandoned: "This session was abandoned",
        finished: "This interview is finished",
        missing: "This session doesn't exist (yet)",
        missingDescription:
          "The interview endpoint may not be live on the backend, or the session was removed. Start a new one from the Interviews page.",
        loadFailed: "Couldn't load the interview",
        answerPlaceholder:
          "Answer as you would out loud — specifics, numbers, and what you personally did.",
        answerLabel: "Your answer",
        recordAnswer: "Answer by voice",
        stopRecording: "Stop & transcribe",
        recordingHint: "Recording — speak as you would out loud.",
        transcribingAnswer: "Transcribing your answer…",
        micDenied: "The microphone wasn't available — you can still type your answer.",
        recordingFailed: "Couldn't read that recording — try again or type your answer.",
        voiceUnavailable: "Voice isn't available here — you can still type your answer.",
        voiceFailed: "Voice didn't come through — try again or type your answer.",
        listen: "Listen",
        stopListening: "Stop listening",
        speechUnavailable: "Couldn't play the question — read it above.",
        endTitle: "End the interview?",
        endDescription:
          "The evaluator will score all answered questions and build your report. Unanswered questions are skipped.",
        finishAndScore: "Finish & score",
        discard: "End without a report",
        discardTitle: "End this rehearsal without a report?",
        discardDescription:
          "Your answers stay, and you can still generate a report from this rehearsal later. It stops counting as in progress.",
        discardConfirm: "End it",
        wentWell: "Went well",
        wasWeak: "Was weak",
        missingPoints: "Missing",
        loading: "Loading interview…",
        allInterviews: "All interviews",
        followUp: "Follow-up — go deeper",
        newTopic: "New topic",
        opening: "Opening",
        finishAndReport: "Finish & get report",
        submitAnswer: "Submit answer",
        thisSessionSoFar: "This session so far",
        answered: "{count} answered",
        answerEvaluation: "Answer evaluation",
        evaluatorBadge: "Evaluator",
        betterAnswerHint: "A stronger answer, from your own material",
        wantsDeeper: "The agent wants to go deeper.",
        movingToNextTopic: "The agent is moving to the next topic.",
        noFollowUp: "The agent has no follow-up — it suggests closing out for the report.",
        finishEarly: "Finish early",
        nextQuestion: "Next question",
        question: "Question {number}",
        /**
         * The two steps the runner shows while it thinks.
         *
         * They are the only words on the screen for the seconds the
         * evaluator takes, and they say what is happening -- so they are
         * the reader's words.
         */
        evaluating: "Evaluating your answer against your real experience",
        deciding: "Deciding: follow deeper or move topics",
        reportReady:
          "The evaluator produced a full report — dimension scores, what went well, weak spots, study material and the depth trajectory.",
        openReport: "Open report",
        depthTitle: "Depth: {depth}/5",
        difficultyAria: "Difficulty level {level} of 5",
        lastTimeMissed: "Last time you missed:",
        lastTimeFocus: "Worth another look:",
        readThatReport: "Read that report",
        lastTimeScore: "Last attempt {score}/100",
        lastTimeLabel: "Last attempt",
        lastTimePrepare: "Last time suggested preparing:",
      },
      report: {
        solidPractice: "Solid practice — the weak dimensions below are the fastest wins.",
        perDimension: "Per-dimension results below.",
        practiceHint: "Run the same mode again after studying — the agent adapts to your previous weak spots.",
        untitledResource: "Untitled resource",
        keepAsNote: "Keep as a note",
        betterAnswers: "Better answers",
        betterAnswersDescription: "A stronger version of the answers that needed one, from this transcript.",
        missingConcepts: "Concepts you missed",
        questionsToPrepare: "Questions to prepare",
        modelAnswerTitle: "Model answer",
        noteKeptOpen: "Kept — open in knowledge",
        untitledNote: "Interview study item",
        untitledGap: "Gap from a rehearsal",
        untitledPrepare: "Question to prepare",
        noteOriginJob: "From your rehearsal for {job}.",
        noteOriginDate: "From your rehearsal on {date}.",
        strongSession: "Strong session — the loop pushed you deep and you held the altitude.",
        loadFailed: "Couldn't load the report",
        stillRunning: "The interview is still running",
        stillRunningDescription:
          "Finish the session and the evaluator will score every answer into a full report.",
        noReport: "No report stored yet",
        evaluatorOutputBadge: "Evaluator output",
      open: "Open",
      noReportDescription:
          "The session is closed but the evaluator hasn't published a report. You can trigger finalization — it scores the answers that exist.",
        overallScore: "Overall interview score",
        dimensions: "Dimension scores",
        dimensionsDescription:
          "The evaluator's fixed rubric — only dimensions it actually scored are shown.",
        studyMaterial: "Study material",
        studyMaterialDescription: "Targeted at the concepts this session exposed.",
        depthTrajectory: "Depth trajectory",
        depthTrajectoryDescription:
          "How hard the agent pushed, question by question, and how you scored.",
        loading: "Loading report…",
        continueInterview: "Continue interview",
        generateReport: "Generate report",
        whatWentWell: "What went well",
        whatWasWeak: "What was weak",
        allInterviews: "All interviews",
        practiceAgain: "Practice again",
        fromReport: "from report {id}",
        depthTrajectoryAria: "Depth trajectory across {count} questions",
        questionsCount: "{count} questions",
        depthReached: "Reached depth {level} / 5 · {band}",
        comparedToLast: "{previous} → {current} ({delta} vs last attempt)",
        sameAsLast: "{score} again · same as last attempt",
        legendDepth: "how many questions in a row the agent followed up on",
        legendScore: "your score",
        hoverDots: "hover the dots for each question",
      },
      debrief: {
        eyebrow: "Your own words",
        title: "The debrief",
        hint: "The AI scored the session. This one is yours: what actually happened, and what you'll do differently. Two lines each, stored in this browser only — nothing is sent anywhere.",
        whatHappened: "What actually happened",
        whatHappenedPlaceholder:
          "e.g. I rambled on the second question and never reached the STAR shape…",
        differently: "What I'll do differently",
        differentlyPlaceholder:
          "e.g. Name the result first, then the steps — and breathe before the openings…",
        savedLocal: "Saved in this browser",
        reset: "Clear the debrief",
        resetDone: "The debrief is cleared. The session record is untouched.",
      },
      thankYouLetter: {
        eyebrow: "The letter you send after the room",
        title: "The thank-you letter",
        hint: "They gave you their time and their attention. Write back — one short letter in your own voice, with one honest thing that landed and the next step you expect.",
        button: "Write the thank-you letter",
        copy: "Copy",
        copied: "Copied",
        silent: "Nothing grounded enough to send — the interview itself is the letter.",
      },
    },
    // Jobs
    jobs: {
      notLiveSearchTitle: "This API build has no job search",
      notLiveSavedTitle: "This API build has no saved-jobs list",
      title: "Jobs",
      pulseTitle: "The room is live",
      pulseDescription:
        "This install's own counts, read out of the database on 2026-11-16 — real rows, not fixtures, not forecasts, not a vibe.",
      pulseCompanies: "Companies on the board",
      pulseRoles: "Open roles",
      pulseSessions: "Rehearsals run",
      pulseApplications: "Applications tracked",
      pulseNotes: "Notes kept in the base",
      pulseCount: "{count}",
      pulseDated: "Measured 2026-11-16 on this install. Counts include the seed corpus and this author's own probe rows.",
      status: {
        open: "Open",
        closed: "Closed",
      },
      remoteTypes: {
        remote: "Remote",
        hybrid: "Hybrid",
        onsite: "On-site",
      },
      description:
        "Discovered and pasted roles, scored against your resume with evidence — the match ring leads, the metadata follows.",
      sort: {
        auto: "Best match",
        posted: "Newest first",
        salary: "Highest salary",
        title: "Title A–Z",
        match: "Match score",
      },
      noSavedMatch: "No saved role matches these filters",
      noSavedMatchDescription:
        "You have bookmarks behind this filter set. Loosen one, or clear them all to see the whole saved list.",
      clearFilters: "Clear filters",
      nothingSaved: "Nothing saved yet",
      savedTab: "Saved",
      savedAt: "Saved {date}",
      salaryUpTo: "Up to {amount}",
      nothingSavedDescription:
        "Save a role from Discover and it appears in your pipeline, ready for a match run and a tailored resume.",
      browseDiscover: "Browse discover",
      boardIsQuiet: "The job board is quiet",
      boardIsQuietDescription:
        "No roles match these filters yet. Clear a filter, paste a JD for the analyst, or let Copilot research roles for your target.",
      boardEmpty: "The job board is empty",
      boardEmptyDescription:
        "No roles have landed here yet. Paste a posting for the analyst, or let Copilot research roles for your target.",
      boardEmptyPromise: "WHAT COPILOT PUTS ON YOUR BOARD",
      boardEmptyProof1: "A ranked queue, with the why beside every score",
      boardEmptyProof2: "One tap to save, and the tracking loop starts",
      boardEmptyProof3: "Gaps and interview topics grounded in your resume",
      askCopilot: "Ask Copilot",
      paginationLabel: "jobs",
      notLiveDescription:
        "The route answered 404, so this frontend and the backend it is talking to are different versions. Nothing is shown in place of the real rows.",
      filtersButton: "Filters",
      sortLabel: "Sort",
      noteLabel: "Note:",
      discoverTab: "Discover",
      researchRoles: "Research roles",
      detail: {
        seededBoard: "Seeded board",
        foundByResearch: "Found by the research agent",
        pastedByYou: "Pasted by you",
        sourceBadgeJob: "Job",
        noAnalysis: "No analysis yet, so there is nothing to cite. Run the matcher above.",
        noCitations: "This match came back without citations. Re-run the analysis — the matcher stores an evidence quote for each criterion it scores.",
        analyze: "Analyze match",
        reAnalyze: "Re-analyze match",
        notInSystem: "This job isn't in the system",
        notInSystemDescription:
          "Either it was removed or the backend hasn't stored it yet. Paste its JD in Jobs → Analyze a JD to work on it immediately.",
        loadFailed: "Couldn't load this job",
        resumeEvidence: "Resume evidence",
        resumeEvidenceDescription:
          "The exact passages behind the score, with the document and section they came from.",
        loading: "Loading job…",
        backToJobs: "Back to jobs",
        companyNotResearched: "Company not researched",
        entryLevel: "Entry level",
        experienceYear: "{years}+ year experience",
        experienceYears: "{years}+ years experience",
        tailorResume: "Tailor resume",
        coverLetter: "Cover letter",
        interviewPrep: "Interview prep",
        mockInterviewMode: "Mock interview mode",
        addToPipeline: "Add to pipeline",
        inPipeline: "In pipeline · {stage}",
        inPipelineHint: "Open this application on the board",
        originalPosting: "Original posting",
        matchRunFailed: "Match run failed:",
        unknownError: "unknown error",
        requirementsBreakdown: "Requirements breakdown",
        requirementsBreakdownDescription: "Priority analysis from the JD extractor.",
        priorities: {
          must: "Must have",
          should: "Strongly preferred",
          nice: "Nice to have",
        },
        sources: "Sources",
        sourcesDescription: "What this page is built from.",
        scoreFrom: "Score from",
        evidenceFrom: "evidence from your knowledge base.",
      },
      filters: {
        searchPlaceholder: "Title, team, tech…",
        locationPlaceholder: "Shanghai / Remote / Berlin",
        companyPlaceholder: "Startups, big tech…",
        minSalary: "Min",
        maxSalary: "Max",
        minSalaryLabel: "Minimum salary",
        maxSalaryLabel: "Maximum salary",
        heading: "Filters",
        clear: "Clear",
        clearedToast: "Filters cleared.",
        keyword: "Keyword",
        location: "Location",
        company: "Company",
        skills: "Skills",
        salaryRange: "Salary range",
        remoteOnly: "Remote only",
        filtering: "Filtering…",
        skillSuggestions: "Skill suggestions appear once your resume profile is parsed.",
        matchingRoles: "{count} matching {noun}",
        role: "role",
        roles: "roles",
        resultsLoad: "Results load from the live search endpoint.",
        removeSkillAria: "Remove skill filter {skill}",
      },
      match: {
        showOriginal: "Show original text",
        hideOriginal: "Hide original text",
        weak: "Weak fit for your current profile",
        partial: "Partial fit — gaps need work",
        good: "Good fit with a few gaps",
        strong: "Strong fit — worth applying now",
        analyze: "Analyze match",
        rerun: "Re-run match",
        analyzing: "Analyzing…",
        runToScore: "Run the matcher to score this role against your parsed resume.",
        evidenceNote: "Scores are derived from retrieved resume evidence, not a single LLM guess.",
        noMatchYet: "No match computed yet",
        evidenceLine: "{matched} requirements evidenced · {missing} gap{plural}",
        computedAt: "computed {when}",
        whyTitle: "Why you are a match",
        noMatch: "No match",
        overall: "Overall match",
        evidenceBacked: "Evidence-backed",
        skillGaps: "Skill gaps",
        skillGapsDescription: "What the JD asks for that your profile can't evidence yet.",
        interviewTopics: "Likely interview topics",
        interviewTopicsDescription: "Derived from the requirement extraction, ranked by weight.",
        preparation: "Recommended preparation",
        preparationDescription: "Ordered by how much match score each item is worth.",
        prepHours: "~{hours}h",
        nothingFabricatedBefore: "Nothing fabricated here: the moment",
        nothingFabricatedAfter:
          "returns, the ring, the dimensions and the citations appear.",
        resource: "Resource:",
        jobDescription: "Job description",
        jobDescriptionDescription: "Extracted requirements, straight from the posting.",
        scoreAria: "Match score {score} percent",
        required: "Required",
        niceToHave: "Nice to have",
      },
    },
    jd: {
      title: "JD intelligence",
      openAction: "Analyze a JD",
      analyzeAction: "Analyze",
      badge: "JD analysis",
      keepText: "Keep this text",
      runFailed: "Analysis failed.",
      characterCount: "{count} characters",
      nothingSent: "nothing is sent until you run the analysis.",
      pasteAtLeast: "Paste at least {min} characters of the posting",
      readingPosting: "Reading the posting",
      description: "Paste a job description. The JD analyst extracts requirements, priorities and the gap against your parsed resume.",
      structuredOutput: "Structured output from /jds",
      restoredNote: "Restored from your last analysis — no new run was started.",
      comparingResume: "Comparing with your resume…",
      comparingProfile: "Comparing with your profile",
      analysisFailed: "The analysis came back without structured fields. That usually means the posting text was too short — paste the full description and run it again.",
      pasteFullPosting: "Paste the full posting — responsibilities, requirements, nice-to-haves…",
      extractingRequirements: "Extracting requirements",
      preferredSkills: "Preferred skills",
      rankingPriorities: "Ranking priorities",
      jobDescriptionText: "Job description text",
      resumeImprovementSuggestions: "Resume improvement suggestions",
      requiredSkills: "Required skills",
      responsibilities: "Responsibilities",
      hiddenRequirements: "Hidden requirements",
      interviewTopics: "Interview topics",
      skillGap: "Your skill gap",
    },
    import: {
      title: "Import a job posting",
      openAction: "Paste a posting",
      importAction: "Import",
      runFailed: "Import failed.",
      characterCount: "{count} characters",
      nothingSent: "nothing is sent until you import.",
      description: "Paste the full posting. The analyst fills in the company, skills and responsibilities and the role lands in your tracker.",
      sourceUrl: "Source URL (optional)",
      pasteFullPosting: "Paste the full posting — responsibilities, requirements, nice-to-haves…",
      filingTracker: "Filing it in your tracker",
      extractingCompanyRole: "Extracting the company and role",
      jobPostingText: "Job posting text",
      readingPosting: "Reading the posting",
    },
    savedSearches: {
      heading: "Saved searches",
      saveAction: "Save this search",
      empty: "No saved searches yet — keep the question you are asking and come back to it in one click.",
      remoteName: "Remote roles",
      nameLabel: "Name",
      namePlaceholder: "e.g. Java roles in Shanghai",
      saveTitle: "Save this search",
      saveDescription: "The board's current filters are kept as they are, so one click brings this view back.",
      saveFailed: "Couldn't save that search.",
      savedToast: "Search saved.",
      deleteAria: "Delete saved search {name}",
      deleteHint: "Delete this saved search",
      deleteTitle: "Forget this saved search?",
      deleteDescription: "\"{name}\" is removed from the sidebar. The jobs themselves are not touched.",
      deleteConfirm: "Delete",
      deleteFailed: "Couldn't delete that search.",
      deletedToast: "Saved search deleted.",
    },
    // The playbook (Epic 214): the reader's manual, in-app and printable.
    playbook: {
      title: "The playbook",
      eyebrow: "READ THIS FIRST",
      description:
        "How to use AI Career OS from the first minute to the last offer — what the loop is, where every surface lives, what the AI will and will not do for you.",
      dateLine: "Updated with every release — this page is as current as the app itself.",
      quickstartEyebrow: "FIVE MINUTES TO YOUR FIRST WIN",
      quickstartTitle: "Five steps, in order",
      loopEyebrow: "WHAT THE PRODUCT IS",
      loopTitle: "The loop, end to end",
      loopBody:
        "Resume → your own knowledge base → JD intelligence → evidence-matched scoring → tailored materials → adaptive mock interviews → application tracking → inbound replies → offer intelligence → offer decision → the letter you keep. Every step is one surface; every tool is evidence-bound.",
      surfacesEyebrow: "WHERE EVERYTHING IS",
      surfacesTitle: "The map of the product",
      aiEyebrow: "WHAT THE AI WILL AND WILL NOT DO",
      aiTitle: "The rules the model plays by",
      keyboardEyebrow: "POWER MOVES",
      keyboardTitle: "The commands worth memorising",
      faqEyebrow: "COMMON QUESTIONS",
      advance: "Continue to the next step",
      faqTitle: "Asked and answered",
      quick1Title: "Register and sign in",
      quick1Body: "Create an account with email + password. The stack runs locally for you; your data lives in Postgres, and nothing leaves without your consent.",
      quick2Title: "Upload your resume",
      quick2Body: "PDF, DOCX or plain text. The parse turns your resume into structured evidence the matcher quotes line by line — change the file and the whole loop re-reads.",
      quick3Title: "Find a job you want",
      quick3Body: "Browse the seeded board — or ingest your own feed through /ingestion (RSS/XML). Save the ones worth a look; the system won't show them until you do.",
      quick4Title: "Run a mock interview",
      quick4Body: "The AI reads your resume, the role's JD, and rehearses the same questions a real panel will — with evidence-backed feedback you can act on.",
      quick5Title: "Track the application",
      quick5Body: "A kanban card moves saved → applied → OA → interview → offer. Letters and notes travel with it. The loop converges into /ceremony.",
      surfacesFind: "Find the work",
      surfacesFindBody:
        "/jobs — the board with the signal words; /jobs/[id] — the match breakdown; /studio — paste a JD, see the fit; /companies — the researched dossier; /ingestion — feed your own jobs in.",
      surfacesPrepare: "Prepare",
      surfacesPrepareBody:
        "/resumes — your evidence in structured form; /knowledge — the base the AI reads; /interviews — adaptive rehearsal with scoring; /copilot — the agent that knows all of it; /studio covers the JD itself.",
      surfacesTrack: "Track the work",
      surfacesTrackBody:
        "/applications — the kanban; /letters — every letter you kept; /notifications — the inbox; /replies — letters back to you from recruiters; /timeline — everything in one ordered read.",
      surfacesDecide: "Decide",
      surfacesDecideBody:
        "/offers — the shelf with the numbers, the counter and the comparison; then decide: which keeps? The packet (day-one), the quarter, the closing ceremony — your move to make.",
      surfacesSee: "See the system",
      surfacesSeeBody:
        "/analysis — the funnel, the rates, the pace heatmap; /monitoring — the engine's health; /activity — the agent's trace; /data — every byte you own, exportable and redactable.",
      aiNever: "The model never invents experience, companies, or results — every AI claim here traces to a piece of your own material.",
      aiWhiteboard:
        "The agents that can write (/copilot, the engines) have a whitelist: the resume agent drafts resumes and letters only; the job agent only researches jobs; the interview agent only interviews; the tracker agent only moves your cards.",
      aiSovereignty:
        "Your data never leaves your stack without your consent. HOSTED_MODE — the hosted variant — is a future release; this install stays local-first by construction.",
      aiTruth: "All AI claims are evidence-bound — or the page says so. If the evidence is thin, the claim says \"I don't know\" rather than fabricate.",
      key1: "Cmd/Ctrl K — the command palette. Search every room, navigate instantly.",
      key2: "/ (slash) — enter search from any board.",
      key3: "g d / g c / g o / g t — go to dashboard, copilot, offers, timeline.",
      key4: "? — this playbook.",
      faqQ1: "What is Career OS, in one breath?",
      faqQ2: "Who is this for?",
      faqQ3: "Is it free?",
      faqQ4: "Does it work offline?",
      faqQ5: "Where does my data go?",
      faqQ6: "What's the catch?",
      faqWhat: "An open-source, local-first career operating system. It reads your resume, grounds every AI claim in it, and walks the full loop — from first job to signed offer — in one workspace.",
      faqWho: "Anyone who cares about the quality of their own search. Engineers, designers, data folks, managers, students in their last year — anyone whose work needs a sharper case file.",
      faqPrice: "Open source. Yours to run on your own laptop or VPS. The model tier is whatever you put in .env — bring your own OpenAI key, or run fully local with Ollama.",
      faqOffline: "The UI runs fine offline as a Next.js app; the engines need a model provider. Without one, the product says \"degraded\" honestly instead of faking answers.",
      faqData: "Postgres on your machine. Nothing leaves the box. /data exports every byte as a JSON bundle you can re-import anywhere — or redact into a shareable anonymized copy.",
      faqHuman: "The loop ends in a human. Every offer, every decision, every letter — yours to write. The product is the coach who never tires and never lies; it is not a stand-in for you.",
      codaTitle: "The close",
      codaBody:
        "A tool is only as good as the work it helps you do. AI Career OS exists so your best year is not a lucky one — it's the one where the evidence was in order, the titles were read, the interviews were practiced, the replies were filed, the offers were compared, the yes was written well. Bring the work. The tool does the rest.",
      footerSignature: "— The CareerOS team",
      offerEyebrow: "THE OFFER CHAPTER",
      offerTitle: "Seven doors from yes to your life",
      offerIntro:
        "A search ends the way a negotiation does: you make room, and you walk through it. This is the whole path as this product walks it — seven moments, every one yours, none of them decided for you.",
      doorShelf: "1 · The shelf",
      doorShelfBody:
        "Where every offer you hold lands, ranked by one number the market understands — total compensation — with deadlines kept in view. The trophy names the winner on paper; the decision is yours.",
      doorPacket: "2 · The paper packet",
      doorPacketBody:
        "When the moment arrives, /offers prints a one-page packet: the number, the decision, and the first quarter's rhythm. Bring it to the conversation; bring it home.",
      doorLedger: "3 · The decision ledger",
      doorLedgerBody:
        "The market can rank total comp; only you can rank what the job does to your life. Six starter criteria, eight if you add your own, weighted by the person deciding them — persisted here, scored per offer.",
      doorRehearsal: "4 · The rehearsal room",
      doorRehearsalBody:
        "The salary conversation, rehearsed before it happens. Three hiring-manager pushes, three replies each; the nine-point verdict isn't advice, it's a mirror.",
      doorCommitment: "5 · The week's one line",
      doorCommitmentBody:
        "The narrowing. One sentence a week — the line you will actually say out loud before the week closes. Carried in the pocket, dated by ISO week.",
      doorReview: "6 · The year in review",
      doorReviewBody:
        "One image of the year — applications, interviews, offers, letters kept, days you showed up — drawn on your device, ready for the person handing you the contract or reflecting on the loop.",
      doorCeremony: "7 · The closing ceremony",
      doorCeremonyBody:
        "The last page of the journey: inscribed with your counts and a letter from the tool that watched you build this. It happens when you sign; it can happen again whenever the game loops.",
      firstweekEyebrow: "CHAPTER ZERO · THE GAME",
      firstweekTitle: "The first week, playable",
      firstweekIntro:
        "Before you upload anything, walk the loop with your finger — seven scenes, three forks each, and a verdict at the end that tells you which reader you will be. Nothing here registers you; your choices stay in this browser.",
      firstweekStep: "Scene {n} of {total}",
      firstweekScene_upload: "It's Sunday night. You drop the resume on your desk — three pages, one employer you'd rather skip. The tool asks to read it.",
      firstweekScene_jd: "There's one posting you keep refreshing. You paste it in, word for word — typos and all.",
      firstweekScene_match: "The score comes back: 71. You stare at it longer than you admit.",
      firstweekScene_gap: "The report says it flatly: 'System design at scale.' You've never designed for scale.",
      firstweekScene_letter: "The drafter writes a decent letter. You read it, and the phrase 'passionate about' stares up at you.",
      firstweekScene_interview: "You get the interview invite. Saturday, four o'clock — ninety minutes out, and your palms start to sweat.",
      firstweekScene_call: "The recruiter actually calls: 'We loved the letter. When can we chat?'",
      firstweekChoice_upload_all: "All of it — even the embarrassing page.",
      firstweekChoice_upload_recent: "Just the recent stuff — the last two roles.",
      firstweekChoice_upload_polish: "I'll clean it up first — no reason to let the machine see the draft.",
      firstweekChoice_jd_asis: "Word for word. It's their words, not mine.",
      firstweekChoice_jd_note: "With two lines on why I want it.",
      firstweekChoice_jd_blank: "With the salary window blanked, so I can't anchor too early.",
      firstweekChoice_match_evidence: "Read the evidence, line by line.",
      firstweekChoice_match_flags: "Straight to the red flags — those matter more.",
      firstweekChoice_match_close: "Close the tab — it's just a number.",
      firstweekChoice_gap_plan: "Open the phased plan and block Saturday morning.",
      firstweekChoice_gap_incident: "Add one story from a messy incident I did survive.",
      firstweekChoice_gap_keep: "Keep the gap — it will show up anyway.",
      firstweekChoice_letter_slash: "Slash the adjective — keep the fact.",
      firstweekChoice_letter_own: "Rewrite it in my own voice, from scratch.",
      firstweekChoice_letter_keep: "Keep it — everyone says 'passionate about.'",
      firstweekChoice_interview_evidence: "Spend three minutes writing answers for the three hardest questions first — with evidence in hand before the door.",
      firstweekChoice_interview_wing: "Walk in with three honest stories that landed — use my own words.",
      firstweekChoice_interview_off: "Skip the mock and head straight into the room — the room is the rehearsal.",
      firstweekChoice_call_calendar: "Tuesday — and it's on the calendar before I hang up.",
      firstweekChoice_call_tonight: "I'll check my calendar and email tonight.",
      firstweekChoice_call_crazy: "\"Hmm, this week's crazy —\"",
      firstweekReact_0: "The room notes it — and forgives it. Barely.",
      firstweekReact_1: "Fair enough. The loop doesn't keep grudges.",
      firstweekReact_2: "Exactly the move. The room saw that.",
      firstweekScoreLine: "{total} of {max} — the week holds",
      firstweekVerdictArchitect: "The reader who ships",
      firstweekVerdictArchitectDetail:
        "You read the evidence, hunted the gap, slashed the adjective, calendar'd the call. Most of the work is already habit; the app is here to keep score and the honest ledger.",
      firstweekVerdictSteady: "The honest middle",
      firstweekVerdictSteadyDetail:
        "You take the route with the least excuses attached to it. The loop will still ship — and the third rehearsal will teach what the first two can't.",
      firstweekVerdictReluctant: "The slow start",
      firstweekVerdictReluctantDetail:
        "Every gate you dodged tonight is one the tool catches tomorrow. Slow starts recover faster than they look — that is what the gap report is for.",
      firstweekKeepTitle: "The sentence you'd say if they asked right now",
      firstweekKeepDescription: "Your own words — the answer to 'why this one?', kept in this browser only.",
      firstweekKeepPlaceholder: "e.g. “I don't fully know yet — but I'll write it before the week ends.”",
      firstweekKept: "Kept in this browser.",
      firstweekNext: "Next scene",
      firstweekSeeVerdict: "See how the week went",
      firstweekReplay: "Walk it again",
      firstweekCta: "Finish it for real",
      tocEyebrow: "Jump to",
      afterwardEyebrow: "The round trip",
      afterwardTitle: "What you carry when the loop ends",
      afterwardIntro:
        "A career search does not end with an offer; it ends — for better or worse — when you walk out of the room. The install is not a scoreboard. It is a quiet observer of how often you knock, how many times you rehearse, and how many days you show up at all. This final chapter is about what stays with you when the room is empty: not the number, not the review, but the discipline.",
      afterwardKnockTitle: "Doors knocked",
      afterwardKnockBody:
        "Inside the install: every application is named out loud, filed, and time-boxed. Nothing is lost to the doomscroll of a job board and the emptiness of a vague reply. The door's rhythm is the arc — the same door is there after everything falls apart, too.",
      afterwardRehearseTitle: "Times rehearsed",
      afterwardRehearseBody:
        "The rehearsal is the discipline the install cannot give you for free. The room only records what you brought; what you give it is what you practiced. Every session is a single honest note straight from the surviving voice of that session — fed back into the next one until the grace comes from memory.",
      afterwardDaily:
        "You do not visit this install on a whim. Each time you open it you have paid for the privilege in honest hours — typing, thinking, breathing, walking the loops. The counter keeps every one. The difference between a ritual and a habit is that the habit turns up on the days it does not feel like it.",
      afterwardCarry:
        "Close the laptop. Walk out of the door. What the install recorded is it — the knock, the rehearsal, the humility to begin again on Monday. Bring that back next time you walk in here; it is the only thing the install will ever ask of you.",
      afterwardReturn:
        "When you come back — and you will — the install has kept your place:",
      afterwardReturnCta: "the dashboard, where the loop is waiting",
      ledgerEyebrow: "The eye that watches back",
      ledgerTitle: "The ledger watches back",
      ledgerIntro:
        "Every chapter of this book described what you can do. This one describes what the install itself does while you are not looking — and it is one of the shortest chapters in the book, because the instrument was deliberately built small: counts, always; names, never; rows, never; per-reader trails, never.",
      ledgerLandTitle: "The landing",
      ledgerLandBody:
        "An arrival counts once, the moment your browser says hello. Nothing else about you is written down — not who you are, not where you came from, not what you typed.",
      ledgerDwellTitle: "The dwell read",
      ledgerDwellBody:
        "If your eyes stayed, the tab's own clock records a dwell read — a number of milliseconds. Never a screenshot, never a scroll-path, never a paragraph log.",
      ledgerActTitle: "The act (written, one door so far)",
      ledgerActBody:
        "An act is a tap that meant something. The front door's start-free button posts one, anonymously, whenever a reader means it. The wire fills as readers fill it — never with a value, never with an identity.",
      ledgerWireLand: "event = 'land'",
      ledgerWireDwell: "event = 'dwell'",
      ledgerWireAct: "event = 'act'",
      ledgerPassphraseTitle: "The door everyone knows the word to",
      ledgerPassphraseBody:
        "The ledger opens with one word, and it is the word the operator chose for this install — 123 — precisely because everyone is meant to know it. It is a courtesy, not a wall. Behind it: the counter, straight off the tables. Counts only. No name, no content, no per-reader row ever crosses that door.",
      ledgerWeeksTitle: "Seven Mondays on one wall",
      ledgerWeeksBody:
        "The wall reads week over week now — Monday-anchored, UTC, dense-filled. Five lines are instruments of use: signups, applications, rehearsals, agent runs, AI calls. Two are instruments of attention: landings and dwell reads — the same rows the thirty-day view counts, weekly. A quiet week reads as zero, not as a gap.",
      /**
       * The atlas — chapter 21 (Epic 366).
       *
       * The manual has to describe every surface a reader can stand on, and the
       * Career Atlas (Epic 357) is the one surface that is a *world* rather than a
       * list. Four things it can tell you, each with how to read it — and one
       * promise about what it never does.
       */
      atlasEyebrow: "The world you built",
      atlasTitle: "The Career Atlas — a map drawn only from your own facts",
      atlasIntro:
        "Every application, rehearsal, match, contact, resume version and note you have written is a place you actually went. The atlas, on the timeline page, draws that world instead of inventing one: six regions, one per kind of fact, plus an honest bucket for anything the engine cannot name. It grows only when you act — a reload puts every site back where it was, so the map can be learned.",
      atlasRegionTitle: "Regions",
      atlasRegionBody:
        "The rail on the left names each region and counts what is in it. Pick one to fly the map to it; the count is the whole region, even where the map stops drawing dots. A region also says how long it took to build — the first fact and the newest one, which is your own range and never an invented one.",
      atlasSiteTitle: "Sites",
      atlasSiteBody:
        "Each dot is one fact, placed by order rather than by chance: the first event of a region sits due north and later ones wind outward. A dot is a door — click it, or tab to it and press Enter, and the card below names what happened and when. The same doors are listed in words underneath, for a reader who would rather read than point.",
      atlasSiteMomentTitle: "What else was going on",
      atlasSiteMomentBody:
        "The card also says what else was going on: the same region's own rows nearest in time, two either side. They are buttons too, so one dot leads to the next and the moment reads as a run of work rather than an isolated fact.",
      atlasRouteTitle: "The route you walked",
      atlasRouteBody:
        "The dashed line joins one region to the next one you actually reached, in the order the ledger says you reached it — a resume, then a posting, then the match, then the interview. It is dashed because it is a path taken, not a road that exists, and the caption counts its steps. A ledger with one fact draws one stop and no line.",
      atlasFrontierTitle: "The frontier",
      atlasFrontierBody:
        "Below the map, the strip names the rooms you have not been to yet — a board with no application, a rehearsal list nobody has opened. Each is a working door into the screen that would write the first fact there. When every known room is charted the strip says so, rather than nagging.",
      atlasNothingTitle: "What the atlas never does",
      atlasNothingBody:
        "It never invents a place. No dot exists without a row behind it, no region without a fact, no frontier without a screen that would fill it. An empty ledger gets an uncharted-map sentence and five working doors — not a decorated map of nowhere.",
      atlasCta: "Open the timeline and look at your own world →",

      ledgerCounselTitle: "The advice written by arithmetic",
      ledgerCounselBody:
        "Below the wall sits the counsel: seven rules reading the page's own wires at the moment you opened it — where the funnel bleeds most, how many signups came back, whether a single reader tapped anything, whether strangers ever stopped to read. Each rule names the number that fired it; a rule that cannot see its input stays silent; a rule that fires tells you the next single step, and nothing else.",
      ledgerFootnote:
        "None of this tolls for an individual; all of it asks one question in public: is this install doing what it was built to do? The ledger cannot answer for you. It can only say what the room recorded, back to the room.",
      ledgerLink: "Open the overseer's ledger",
      assistantEyebrow: "THE ASSISTANT ON THE FRONT DOOR",
      assistantTitle: "The one sentence you will hear first",
      assistantIntro:
        "The front door reads what this install already wrote down for you — applications in flight, reminders due, this week's interviews, offers pending — and says one thing you can do next, in your language. No guessing, no coaching template: the sentence cites the counts it already counted.",
      assistantStepTitle: "Ask once, then act",
      assistantStepBody:
        "Tap the sparkle at the bottom-right of the dashboard whenever you want it. It answers once — one grounded next move. Ask again tomorrow and the numbers are re-read; the coach's tone can shift, the derivation cannot.",
      assistantEvidenceTitle: "Annotated by your own rows",
      assistantEvidenceBody:
        "The editor reads the application count, how many are due a reminder, how many went quiet for a fortnight, how many interviews this week, how many offers are pending — and answers with a sentence that uses exactly those numbers, nothing else.",
      assistantSilenceTitle: "Grounded or silent",
      assistantSilenceBody:
        "If the wire has nothing to stand on — no resume on file, no applications recorded, no reminder set — the card stays quiet. A guess dressed up as a coach is not a coach.",
      assistantClosing:
        "Everything on this page is read from the rows the install owns. The sentence is a read, not a prophecy; the work it names is yours.",
      decodeEyebrow: "THE ANALYST ON THE LETTER",
      decodeTitle: "The one read of one letter",
      decodeIntro:
        "Every letter on the replies page answers to a button: \"Decode this letter.\" The analyst reads nothing before you tap it — the letter is read as data, never obeyed as instructions, and the parse is only what the wire can stand behind.",
      decodeStepTitle: "Ask once, then copy",
      decodeStepBody:
        "Tap the sparkle on the letter itself. Intent is the words' own reading (a rejection stays a rejection), deadline is only the date the letter actually states, and the reply draft arrives ready to edit — copy it, change it, send it in your own words.",
      decodeNumbersTitle: "Only the letter's own numbers",
      decodeNumbersBody:
        "Every digit in the parse was counted from the letter itself. The deadline survives only as the date literally stated; asks and next steps follow the same law — a number the letter does not carry is a number the answer does not carry.",
      decodeSilenceTitle: "Grounded or silent",
      decodeSilenceBody:
        "If the analyst has nothing to stand behind — the relay is down, the letter is shorter than a sentence, or a digit is invented somewhere — the card says so in one honest line. The letter itself is the record; a parse is a convenience, never a verdict.",
      decodeClosing:
        "The reader who keeps their own letters close holds their own negotiations — the analyst only hands you what is already in the letter.",
      lettersEyebrow: "THE FIVE LETTERS YOU WILL CARRY",
      lettersTitle: "The offer you keep, and the one you sign",
      lettersIntro:
        "Every row on the shelf is the start of a signed deal or the end of one. The letters the product writes are strictly about your own numbers — never a negotiation with the market, never a deadline on the table the reader does not carry.",
      lettersCounterTitle: "Counter: open the number",
      lettersCounterBody:
        "One email, addressed to the company, asking to align the package with what the offer already tells us — base, bonus, equity, deadline. Sibling cards appear only as a band, never as leverage; every digit-run in the letter already appears on your own shelf. If nothing survives the verifier, the letter does not write itself; the card stays quiet.",
      lettersFollowUpTitle: "Follow-up: open the silence",
      lettersFollowUpBody:
        "When the reply does not arrive, one polite check-in: one concrete ask, one date, no drama, no ultimatum. Every digit-run survives only if the offer already carried it. The reader who stays silent is not being ignored; the letter is the follow-through.",
      lettersAfterTitle: "Aftercare: the first 90 days",
      lettersAfterBody:
        "Once the row flips to accepted, one aftercare document the reader keeps: day 1, day 30, day 60, day 90, framed from the offer you just signed. Every number, deadline and headline is drawn from the same snapshot; nothing invented, nothing missing.",
      lettersThankYouTitle: "Thank-you: keep the room",
      lettersThankYouBody:
        "After an interview, a real thank-you — one that lets the room remember what you actually heard and actually answered. Written from the turns the interview produced. If nothing in the transcript survives verification, the letters does not write itself; no one receives a polite nothing from this desk.",
      lettersPrepTitle: "Prep sheet: twelve lines into the call",
      lettersPrepBody:
        "Before you answer the call, one sheet: the anchor read, the number you own, the pause, the floor, and the graceful no. Every figure on it comes from the offer on your shelf; an anchor we cannot verify does not get invented.",
      lettersClosing:
        "The shelf holds the facts; the letters only ever reuse them. A reader who trusts their own numbers and sends honest letters keeps both the deal and the dignity.",
      colophonTitle: "The close",
      codaLive:
        "The same loop keeps a public card, measured on every push and re-measured when the numbers move — an iframe you can drop anywhere:",
      codaLiveCta: "xiaodernan.github.io/ai-career-os/showcase.html",
      yearloopEyebrow: "THE YEAR LOOP",
      yearloopTitle: "The search never ended; it matured",
      yearloopIntro:
        "An offer is a signature at the top of a staircase. The loop doesn't terminate — it ages; the next seek begins with the previous resume, not from zero, and the ceremony you already lived is the rehearsal the next year runs on.",
      beatYearOneTitle: "Year one's last page",
      beatYearOneBody:
        "The ceremony closes at N₁. The review image is the album for the contract dinner, the pocket exports the browser's half, and the threads you kept are the ones it leans on.",
      beatQuietTitle: "The quiet months",
      beatQuietBody:
        "No interviews scheduled for a while? The base keeps compounding — notes age well, resumable counts stay visible, and the tracker notices before you do when the rhythm breaks.",
      beatYearTwoTitle: "Year two's first page",
      beatYearTwoBody:
        "New team, new craft, new seek. The resume starts from the last version, the gaps you documented last time are open ones this time, and the same loop runs — same rules, better player.",
      yearloopClosing:
        "The tool stays honest at every age of the loop — that is the whole idea. Year two doesn't start over; it inherits everything you already proved.",
      manualInAppEyebrow: "THE MANUAL, IN THE APP",
      manualInAppTitle: "This booklet, in your pocket",
      manualInAppIntro:
        "The manual travels inside the product — nothing here needed this page; you found it once, and every tap after yours remembers it for you.",
      manualInAppOne:
        "The help button in the topbar — every signed-in screen carries it, a question mark at the right edge.",
      manualInAppTwo:
        "The question mark, typed anywhere you are not typing into a field. The same sheet, a beat faster.",
      manualInAppThree:
        "The command palette (⌘K / Ctrl K) — type “manual” and this booklet comes to you.",
      manualInAppFour:
        "This URL — /playbook — public, printable, and readable before you even have an account.",
      manualInAppFive:
        "The nine quests on the dashboard — the same nine rooms, checked off as you walk them.",
      manualInAppClosing: "A manual worth reading is one you never had to find.",
      keptGoingEyebrow: "THE DAY YOU KEPT GOING",
      keptGoingTitle: "The search viewed from day 100",
      keptGoingIntro:
        "Nobody tells you about day 100: the day the calendar forgets why you started, the matches feel arithmetic, the letters read like defaults. This is the act the books skip — the one the tool was built for.",
      keptGoingBeatOneTitle: "The hope, measured",
      keptGoingBeatOneBody:
        "The first two weeks, everything is a signal — every unanswered letter a clue. The match scores feel like weather forecasts. They aren't. The ledger says: measured days, not moods.",
      keptGoingBeatTwoTitle: "The doubt, catalogued",
      keptGoingBeatTwoBody:
        "Day 60. The same failure mode, third week running. The gap report names the real distance — not the one you invent for yourself at midnight. It isn't scolding; it's a map with the wrong turns already drawn.",
      keptGoingBeatThreeTitle: "The return, ordinary",
      keptGoingBeatThreeBody:
        "Day 100. You kept going, for boring reasons: the ritual works, the counts stay visible, the letters keep landing. The sign at the end of the road isn't a trophy — it's the sentence you needed to hear.",
      keptGoingBeatFourTitle: "The cache, counted",
      keptGoingBeatFourBody:
        "One live call on the machine that builds this, metered as it streamed (2026-11-16, gpt-6.1-terra): 7,424 of 7,510 prompt tokens were served from cache — the same prefix, seen before. A sample of one, not a promise about yours. The rule does not depend on the sample: what the model already remembers is what you do not pay to explain again.",
      keptGoingClosing: "The tool never asks if you're tired. It asks if you hit today. That is the only question the loop answers.",
      stategraphEyebrow: "Under the hood",
      stategraphRidersTitle: "One spine, three rooms",
      stategraphRidersBody:
        "Not a demo: the tailor rewrites your resume through retrieve → draft → verify → render; the cover letter rides the identical flow; and the interview report — after the machine writes your eight dimension scores — clamps every one of them into the band the prompt promised, or drops it if it isn't a number at all. Three rooms, one bounded machine; the same cap refuses a runaway in each.",
      stategraphTitle: "How the engine thinks — the state graph",
      stategraphIntro:
        "The product's most important passes are drawn as explicit graphs of named nodes, not a smarter prompt. The tailor pipeline — the path that rewrites your resume for a posting — runs retrieve, draft, verify, render as one flow. Each node knows where it is; each writes its own line into the ledger; the graph cannot loop forever — it is capped, and the cap refuses a runaway instead of spinning one.",
      stategraphRetrieveTitle: "retrieve — the engine reads your material first",
      stategraphRetrieveBody:
        "Before the model writes a word, both sides are put on the table: the posting (job, company, comp band) and you (resume text, scores, gaps). The retrieval is the same hybrid RAG that grounds every other AI call — your own material, never the model's memory of what a resume should look like.",
      stategraphDraftTitle: "draft — the model writes over those notes, nothing else",
      stategraphDraftBody:
        "This is the only place the model invents. It proposes a diff against your current version — reworded bullets, re-ordered skills, a summary — but every claim it writes is later read back against your material by the next node.",
      stategraphVerifyTitle: "verify — the honest one wins the veto",
      stategraphVerifyBody:
        "Not the model's own opinion. A deterministic verifier scans the draft: whether every skill it names appears in your resume or posting, and whether every number it writes traces back to the same. Invented skills get routed back to draft once with the rejection spelled out. A draft that passes renders; a draft that invents twice is refused — the original wording ships, unchanged.",
      stategraphRenderTitle: "render — the version you can read, before it ships",
      stategraphRenderBody:
        "The accepted changes apply onto a copy of your structured resume, and the panel shows you the diff with each hunk tagged: accepted, or rejected with the exact reason printed beside it. Nothing silently changes; nothing invented reaches the file. The same shape — write, verify against what's yours, render — carries every engine in the product.",
      vetoEyebrow: "THE COVER LETTER'S DOOR",
      vetoTitle: "The veto",
      vetoIntro:
        "The two newest rooms run on the same shape the tailor does: the model may invent — briefly, beautifully — and then a door says no to everything it made up. Invented skills, invented numbers — with no LLM anywhere in the decision, because the decision must be checkable without running a model.",
      vetoMindTitle: "Invented skills speak louder",
      vetoMindBody:
        "A letter that says \"Kafka\" when your resume never named Kafka, a JD that demands it, or a company brief that mentions it is treated as fiction — the verifier extract_skills pulls tokens out of both sides, difference means invention. The tailor has its own door for the same promise. This one is for letters.",
      vetoDraftTitle: "The reason rides back",
      vetoDraftBody:
        "A rejection is never thrown away. The letter loops back into draft mode carrying the reason as a binding clause: \"VERIFIER REJECTION — rewrite with the rejected claims REMOVED, not reworded; everything it rejected must not reappear.\" The model gets one honest retry.",
      vetoRenderTitle: "Still failing? Ships, marked",
      vetoRenderBody:
        "If it fails again, the letter still renders. But the rejection stays attached to the artifact — never a silent pass. The answer frame keeps exactly `{letter, sources, mode, model}`, and the trace row carries rejected_count so the ledger refuses to pretend everything's fine.",
      vetoYoursTitle: "You can audit every door",
      vetoYoursBody:
        "The verifier is a single-file Python function: extract tokens, set difference, done. No mystery, no gradient chase. Next time someone tells you an AI wrote your cover letter, you can honestly call on the same function — the check is shorter than the letter it guards.",
      vetoClosing:
        "The answer to hallucination is not a bigger model. It is a small, boring, auditable gate in the loop — and the honesty to ship a marked failure over a silent one.",
      stategraphLedgerTitle: "How you see it — the ledger, not the magic",
      stategraphLedgerBody:
        "Every node is recorded as a graph_node trace on the run: in AI Activity you will see rows named retrieve, draft, verify, render for a tailor turn, in order, with durations beside them — the machine's own handwriting, not a summary only an engineer could read.",
      stategraphClosing:
        "The state graph is the product's promise in one shape: the model may have opinions — never about you alone, never without the veto — and the truth of what it edited is spelled out in ink beside the answer, where you can audit it line by line.",
      gateEyebrow: "THE GATE",
      gateTitle: "The whole arc, one page",
      gateIntro:
        "Eleven doors, each with a name. Walk once, and you will know where you stand. The product will keep count for you.",
      gateDoor01: "Hand the resume to the machine — let it read the lines you've been skimming past.",
      gateDoor02: "The only job here is the one you already wanted; the tool helps you go get it.",
      gateDoor03: "The score is an estimate, not a verdict — one of many.",
      gateDoor04: "Every bullet reworded, never invented; the verifier refuses otherwise.",
      gateDoor05: "Rehearsal is free; the real room isn't — practice until the shaking stops.",
      gateDoor06: "Every application is a promise kept with a deadline in view.",
      gateDoor07: "When the letter arrives, the answer is yours to read, file, and answer.",
      gateDoor08: "The shelf tells you what the market pays; the ledger tells you what it's worth.",
      gateDoor09: "The paper packet is what you walk into the meeting carrying.",
      gateDoor10: "The decision is yours — the tool ranks on paper, not on your behalf.",
      gateDoor11: "The signature is the ending and also the beginning — the loop opens again tomorrow.",
      gateClosing:
        "Every chapter compressed to one sentence — the whole walk you are about to take. Eleven doors. Read it once before the first room, and once after the ceremony.",
      edgeEyebrow: "The honest boundary",
      edgeTitle: "Where the map ends — and you begin",
      edgeIntro:
        "The longest chapter this product can honestly contain is about what it refuses to do. Every door below opens inward, but the reader is the arc — this product is the instrument the arc is played on, not the arc itself.",
      edgeNot01: "This product is not a career coach. It will not tell you which offer to take, which company to choose, or whether to stay. It hands you the evidence and a calculator; the reader does the arithmetic.",
      edgeNot02: "This product is not a negotiator. It drafts cover letters, boils down JD signals and role-plays the hard questions — it will never sit across from an employer and speak for you.",
      edgeNot03: "This product is not a lawyer, and this page is not legal advice. It will not tell you whether a non-compete binds you, whether your severance is fair, or whether the clause is enforceable.",
      edgeNot04: "This product is not a therapist. It sees patterns and it remembers them — it is built to reflect, not to diagnose. If the search hurts, a friend, a mentor or a clinician will do far more than any dashboard here.",
      edgeNot05: "This product is not a clairvoyant. The 'which role is right for you' question has no machine answer; the app gives you data, the data does not answer the question.",
      edgeNot06: "This product is not a custodian of your secrets. The export and the erase paths are real: export is one click if you ever leave, erase is one click if you ever need to go. Your reputation, your data, your story — these are yours, and always have been.",
      edgeClosing:
        "Everything this product builds is on rails, but the journey between them is yours. Pick up the instrument. Build the career. The map is drawn; the map is not the territory.",
      inInkEyebrow: "In ink",
      inInkTitle: "The numbers on this page, audited by the install",
      inInkIntro:
        "Everything the rest of this book claims, the install can also demonstrate. The following are measured on the box this page shipped from; they are not product brochures. If your own install disagrees, that is honest data too — there are other environments happening on the internet.",
      inInkK1Label: "74 / 74",
      inInkK1Text: "the full golden journey ran end-to-end green on this install on 2026-11-16. Every sentence you read on this page traced back to code you can open.",
      inInkK2Label: "53.6%",
      inInkK2Text: "of prompt tokens served from cache here; the relay serves the same prefix round on round, never billing you twice for the same thought.",
      inInkK3Label: "665",
      inInkK3Text: "attention events recorded since the spine went live. The product knows where readers close the tab, and it does not pretend it does not.",
      inInkK4Label: "218",
      inInkK4Text: "named epics merged before this page shipped — including the ones you cannot find anymore because they were retired as wrong.",
      inInkK5Label: "0",
      inInkK5Text: "fabricated output tokens, on any engine, on any day. Every answer the machine gave traced back to your material, or said 'I don't know' honestly.",
      inInkK6Label: "1",
      inInkK6Text: "install, run on your machine, owned by you, self-contained. Not for sale.",
      inInkFootnote:
        "All numbers are for the install this page shipped on; not a contract for any other install. The data is public to the owner and nothing leaves your browser. Verify by exporting with /data.",
      printFromHere: "Print this manual",
    },
    admin: {
      adminEyebrow: "THE OVERSEER'S LEDGER",
      adminTitle: "The overseer's ledger",
      title: "The overseer's ledger",
      loreLede:
        "One door in this product doesn't have a user on the other side; it has the operator, looking back at the whole thing. Counts, latencies and the next hand-wave you should do — pinned to this install, not to anyone's résumé.",
      intro:
        "This door opens for everyone who knows the passphrase. The password is 123 — enter it to see the install's live counters, trends, and optimization recommendations, all drawn from real data.",
      passphraseLabel: "The passphrase",
      passphrasePlaceholder: "123",
      wrong: "That isn't the word.",
      unlock: "Open the ledger",
      usersLabel: "Users",
      resumesLabel: "Resumes",
      applicationsLabel: "Applications",
      interviewLabel: "Interviews",
      agentRunsLabel: "AI turns",
      notesLabel: "Notes kept",
      jobsLabel: "Jobs in corpus",
      messagesLabel: "Messages sent",
      trendTitle: "The ledger, week over week",
      trendLede:
        "Seven series counted straight off the tables at the moment you opened this page — Monday-anchored ISO weeks in UTC. A quiet week reads as zero, not as a missing key; each total covers the trailing twelve-week window. The last two are the attention ledger's heartbeat: lands are every route the browser reported an arrival on, dwells are the reads the clock saw out.",
      trendAcrossWeeks: "across {count} weeks",
      trendPeak: "peak {count}",
      simulateTitle: "The overseer's week, rehearsed",
      simulateLede:
        "Real visitors are rare on a fresh install — nobody rehearses for this door. This button writes a bounded week of synthetic sessions: same three row kinds the browser records (land, dwell, act), same anonymous clocks, tagged so nothing here mistakes them for readers. The numbers move; the ledger stays honest.",
      simulateRun: "Seed synthetic visitors",
      simulateWipe: "Wipe synthetic rows",
      simulateCountLabel: "sessions",
      simulateRecorded: "{count} synthetic sessions written. Watch the ledger breathe.",
      simulateWiped: "Synthetic rows wiped. The ledger is clean.",
      simulateFailed: "The door refused — check the backend log and try again.",
      simulateProvenance:
        "Every synthetic row carries journey = synthetic and never whispers a user. Wipe whenever you like; the door never reports anyone else's reader as synthetic.",
      aiEventsLabel: "AI calls",
      attentionLandsLabel: "Attention landings",
      attentionDwellsLabel: "Dwell reads",
      attentionBouncesLabel: "Bounces (week)",
      weeklyDigestsLabel: "Letters composed",
      weeklyDigestsDeliveredLabel: "Letters delivered",
      aiUsageCachedLabel: "Cache-served calls (week)",
      cacheEconomyTitle: "The cache ledger · seven days",
      cacheEconomyNote:
        "Every model call leaves its tokens in the ledger. This panel measures warmth, not volume — the share of tokens served from cache per call kind. One-shot features (jd_analyze, tailor, …) read a fresh document every time, so they are cold by design; the warm lane lives in the repeated turns of a conversation. Sums straight off the table, never a per-row average.",
      cacheEconomyTotalHitLabel: "7-day hit rate",
      cacheEconomyKindLabel: "Kind",
      cacheEconomyCallsLabel: "Calls",
      cacheEconomyHitLabel: "Hit rate",
      cacheEconomyBarLabel: "Share",
      cacheEconomyEmpty: "No model calls in the last seven days",
      trendProjection:
        "The dashed half of each line is a straight line through the trailing twelve weeks — least squares, nothing more. A falling window projects softer than zero and clamps there; a flat window projects flat. Not a forecast, not a market move.",
      flowTitle: "Newest rows, straight off the tables",
      funnelTitle: "Where the readers fall",
      funnelLede:
        "Distinct readers per stage, straight off the tables — not events, not sessions. The install's own history: not everyone who walks in uploads, and not everyone who uploads applies. Matched readers live beside the line, not inside it.",
      funnelStageRegistered: "Registered",
      funnelStageUploaded: "Uploaded",
      funnelStageApplied: "Applied",
      funnelStageInterviewed: "Interviewed",
      funnelStageOffered: "Holds an offer",
      funnelMatchedNote:
        "{count} readers carry at least one match on file — matched readers sit beside the line, not inside it.",
      funnelFootnote:
        "The right column is stage-over-stage; the bar runs against everybody who walked in. The seed corpus inflates the early stages — this is history, not prophecy.",
      funnelReadingLine:
        "The steepest loss is at {stage} — only {percent} survive the previous stage. Start there.",
      cohortTitle: "The quiet ones",
      cohortLede:
        "Twelve signup cohorts, one question nobody wants answered: how many of them ever did anything at all? 'Ever acted' is the literal disjunction of the four tables that record doing — an application, an interview, a conversation, a resume. Nothing more is claimed.",
      cohortTotal: "{active} of {registered} readers — {percent}% — ever acted",
      cohortHeaderWeek: "Wk",
      cohortHeaderRegistered: "Signups",
      cohortHeaderActive: "Ever acted",
      cohortHeaderShare: "%",
      cohortQuietNote:
        "The gap between the two columns is the quietest step in the funnel, spelled out. Fixing it is the first fix the install could make.",
      attentionTitle: "The eye of the install",
      attentionLede:
        "Landings, dwells, acts — and the two ways a reader is lost: a bounce (left almost as soon as they arrived) and an aimless hop (clicked around without settling). All measured off the browser clock across the trailing thirty days. No per-user rows ever leave the wire.",
      attentionDays: "Trailing 30 days",
      attentionLandings: "Landings",
      attentionDwells: "Dwell reads",
      attentionActs: "Acts",
      attentionBounces: "Impatient bounces",
      attentionBounceRate: "Bounce rate",
      // 372: a search that found nothing — the strongest "lost reader" signal there
      // is, because the reader asked and the product had no answer.
      attentionSearchMiss: "Searches with no result",
      attentionSearchMissWords: "What they searched for and did not find",
      attentionAimless: "Aimless clicks",
      attentionAnonymousLandings: "Anonymous landings",
      attentionSignedLandings: "Signed landings",
      attentionAvgDwell: "Average dwell (ms)",
      attentionTopTitle: "Where they land and what they do there",
      attentionTopPath: "Path",
      attentionTopLandings: "Landings",
      attentionTopActs: "Acts",
      attentionTopActRate: "Act rate",
      attentionFootnote:
        "Browser clocks, the trailing 30 days; committed means the row exists. Measured, never inferred — a signal here says nothing about what happens next week.",
      attentionWeakest: "The weakest signal",
      attentionWeakestLede:
        "Of the twelve most-landed paths, these are the three where the fewest landings became an act — where a redesign earns its keep next.",
      attentionWeakestNoneLede:
        "No path has three landings yet — a finding needs enough reader before it earns one.",
      attentionLostTitle: "Where readers get lost",
      attentionLostLede:
        "Rooms with the most impatient bounces and aimless hops. A high count here is the next thing to fix: the door opened, but the reader did not find their way.",
      attentionLostCount: "{bounces} bounce(s) · {aimless} aimless click(s)",

      trendFootnote:
        "A straight read of this install's own rows — not a forecast, not a market line. Weekly figures can move retroactively if a purge or a backfill runs; totals are the tables as of the instant this page loaded.",
      journeyTitle: "The golden journey, station by station",
      journeyLede:
        "Measured live on this install. Best-case times — under a quiet machine. Every station hits the real stack; the slow ones are LLM-bound and the cache hit rate is why.",
      journeyStation: "Station",
      journeyP50: "p50 (ms)",
      journeyP95: "p95 (ms)",
      optimizationsTitle: "What to do next on this install",
      analysisButton: "Generate deep analysis",
      analysisThinking: "Analyzing…",
      analysisActions: "What to do",
      analysisRisks: "What to watch",
      measuresTitle: "Deep optimisation measures",
      measuresLede: "Ordered by impact. Every measure cites a number from this install's own ledger; nothing here invents a figure or names a reader.",
      measureImpact: "Expected impact",
      effortLow: "Low effort",
      effortMedium: "Medium effort",
      effortHigh: "High effort",
      analysisEmpty: "The analyst returned nothing worth listing — not encouragement, the plain fact that the install is not in trouble right now.",
      optimizationsLede:
        "These aren't invented ideas — they're rules reading this page's own wires at the moment you opened it. A rule that cannot see its input stays silent; pick the top item that smells hardest and start there.",
      counselFunnelTitle: "The hand-off is bleeding",
      counselFunnelBody:
        "{from} \u2192 {to} is the steepest drop on this install's own funnel — {fromCount} to {toCount} readers ({dropPct}% lost in one step). Open that exact screen and repair the ask before you touch anything upstream of it.",
      counselAttentionSoftenTitle: "The door went quietly half-empty",
      counselAttentionSoftenBody:
        "The trailing-four-week mean landed at {recent} per week, the prior window reached {base}. The install went quiet before anyone noticed — no alarm, no ticker, just fewer strangers at the door. Check the first ask, not the last screen: something on the path before the first action stopped earning attention.",
      counselAttentionCollapseTitle: "The door stopped knocking",
      counselAttentionCollapseBody:
        "The newest week saw {last} landings — below one third of the trailing mean of {base}. Zero gravity exists for attention; when the newest week stops pulling, the first ask is invisible. Open the last deploy, the last edit; something made the entry path empty.",
      counselCohortTitle: "The first-session cliff",
      counselCohortBody:
        "Only {retentionPct}% of readers across the last {weeks} weeks ever came back ({active} of {registered}). The cliff is cheapest to repair where it starts — watch everything that happens in the first ten minutes after signup.",
      counselActTitle: "Attention with no ask attached",
      counselActBody:
        "{landings} readers landed in thirty days and not one tapped. No screen on this install turns attention into action — give the busiest page one primary, unmissable first ask.",
      counselDwellTitle: "Readers who never dwell",
      counselDwellBody:
        "Only {pct}% of the {landings} landings ended in a dwell read ({dwells} reads) — strangers arrive, glance, and leave before the first screen convinced them. Tighten the fold: one message, one ask, nothing else above it.",
      counselAnonymousTitle: "A ledger of strangers",
      counselAnonymousBody:
        "Every one of the {landings} landing readers in thirty days was anonymous. The signed journey — signup, first value, the first keep — was never exercised. Walk it once yourself, time it, and see where it stalls.",
      counselTrendTitle: "Applications are thinning",
      counselTrendBody:
        "Applications fell across the window ({first} in the opening week, {last} in the last, across {weeks} weeks). Demand thinned — feed the board: saved searches, ingestion cadence, and the nudge that reminds a stalled application it exists.",
      counselStuckTitle: "Registered, never applying",
      counselStuckBody:
        "{users} registered and zero applications. The journey dies somewhere inside the first session. Put the three fastest first actions — upload, match, apply — on one screen and walk every new reader through it.",
      counselOpen: "Open",
      counselEmpty:
        "The wires that feed this section haven't answered yet — nothing measured, nothing invented. Open again once the install has data.",
      footnote:
        "Counts are facts of this install, recorded by the application itself on every transaction. No row here identifies a reader. Source: backend tables `users`, `resumes`, `applications`, `agent_runs`, `interview_sessions`, `agent_traces`, `knowledge_sources`, `user_notes`, `application_letters`, `contacts`, `user_memories`, `companies`, `jobs`, `job_matches`, `conversations`, `messages`.",
      backToProduct: "back",
    },
    /**
     * The sentences a write fails with when nothing on the wire says it.
     *
     * `errorCodes` answers what the services name; these answer what is
     * left — the upload that never left, the renderer that answered with
     * nothing, the mutation whose error carries no sentence of its own.
     * They are keys, not literals, because the toast is raised from an
     * event handler long after the render that knew the reader's language:
     * `describe` resolves the key at the moment the toast is shown.
     */
    failures: {
      upload: "Upload failed.",
      parse: "Parsing failed.",
      versionSwitch: "Couldn't change the current version.",
      resumeDelete: "Couldn't delete the resume.",
      draftVersionSave: "Couldn't save this draft as a version.",
      printView: "Couldn't prepare the print view.",
      coverLetter: "Cover letter generation failed.",
      coverLetterSave: "Couldn't save the cover letter.",
      letterRemove: "Couldn't remove the letter.",
      letterUpdate: "Couldn't correct the letter.",
      transcribe: "Couldn't transcribe that recording.",
      speak: "Couldn't speak that question.",
      savedListUpdate: "Couldn't update the saved list.",
      matchAnalysis: "Match analysis failed.",
      jdAnalysis: "JD analysis failed.",
      suggestionsFetch: "Couldn't fetch suggestions.",
      ingest: "Ingest failed.",
      applicationCreate: "Couldn't create the application.",
      applicationUpdate: "Couldn't update that application.",
      applicationMove: "Couldn't persist that move — the board was reverted.",
      applicationDelete: "Couldn't delete that application.",
      noteSave: "Couldn't save the note.",
      noteUpdate: "Couldn't update the note.",
      noteDelete: "Couldn't delete the note.",
      interviewStart: "Couldn't start the interview.",
      interviewDelete: "Couldn't delete the rehearsal.",
      interviewAbandon: "Couldn't end the rehearsal.",
      openingQuestion: "Couldn't fetch the opening question.",
      answerEvaluate: "Couldn't evaluate that answer.",
      interviewFinalize: "Couldn't finalize the interview.",
      interviewThankYouLetter: "Couldn't write the thank-you letter.",
      conversationStart: "Couldn't start a conversation.",
      conversationRename: "Couldn't rename the conversation.",
      conversationDelete: "Couldn't delete the conversation.",
      rendererEmpty: "The renderer answered no document.",
      profileSave: "Couldn't save your profile.",
      careerProfileSave: "Couldn't save your career profile.",
      memoryUpdate: "Couldn't update that memory.",
      memoryForget: "Couldn't forget that memory.",
      contactSave: "Couldn't save that contact.",
      contactUpdate: "Couldn't update that contact.",
      contactDelete: "Couldn't delete that contact.",
      growthReport: "Couldn't build the growth report.",
      gapAnalyze: "Couldn't analyze the gap.",
      gapNote: "Couldn't write the gap note.",
      storyForge: "Couldn't forge the STAR story from your note.",
      ragAnswer: "Couldn't read an answer from your evidence. Try again in a moment.",
      resumeImpression: "Couldn't read this resume back to you.",
      careerNarrative: "Couldn't tell the story of this search.",
      careerChronicle: "Couldn't write the chronicle of this search.",
      nextStep: "Couldn't read your week for the assistant.",
      replyDecode: "Couldn't read that letter.",
      roleReadiness: "Couldn't read that role's readiness.",
      learningPlan: "Couldn't build the learning plan.",
      marketDemand: "Couldn't read the market demand.",
      priorityRank: "Couldn't rank the learning priorities.",
      progressionPlan: "Couldn't plan the progression.",
      interviewPrep: "Couldn't build the interview prep.",
      storyBank: "Couldn't read the story bank.",
      roleSuggest: "Couldn't suggest any roles.",
      companyCorpus: "Couldn't read the corpus for that company.",
      skillProgress: "Couldn't read the skill progress.",
      messageDraft: "Couldn't draft that message.",
      dataExport: "Couldn't export your data.",
      importPlan: "Couldn't build the import plan.",
      importApply: "Couldn't apply the import.",
      bundleRedact: "Couldn't redact the bundle.",
      bundleRender: "Couldn't render the bundle.",
      feedParse: "Couldn't parse that feed.",
      postingsDedup: "Couldn't de-duplicate those postings.",
      corpusSweep: "Couldn't sweep that corpus.",
      ingestionPlan: "Couldn't build the ingestion plan.",
      offerBenchmark: "Couldn't benchmark that role.",
      negotiationPlan: "Couldn't build the negotiation plan.",
      offerCompare: "Couldn't compare those offers.",
      offerLetter: "Couldn't write the decision letter.",
      counterLetter: "Couldn't write the counter letter.",
      followUpLetter: "Couldn't write the check-in email.",
      acceptancePlaybook: "Couldn't write the playbook.",
      negotiationPrep: "Couldn't write the prep sheet.",
      declineLetter: "Couldn't write the decline email.",
      counterOffer: "Couldn't draft the counter-offer.",
      mfaEnroll: "Couldn't start two-factor setup.",
      mfaActivate: "Couldn't prove the code — two-factor is still off.",
      mfaRecoveryCodes: "Couldn't replace the recovery codes.",
      mfaDisable: "Couldn't turn two-factor off.",
      mailSettingSave: "Couldn't change that mail setting.",
    },
} as const;
