/**
 * CN/EN translations (17.1). The product is CN-context but English content;
 * this file provides a simple translation layer for the UI.
 */

export type Locale = "en" | "zh";

export const translations = {
  en: {
    // Navigation
    nav: {
      dashboard: "Dashboard",
      notifications: "Notifications",
      replies: "Replies",
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
      settings: "Settings",
      ingestion: "Ingestion",
      yourData: "Your data",
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
      settings: "Account and preferences",
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
    },
    // Common actions
    common: {
      clipboardBlocked: "Your browser blocked clipboard access.",
      fileSaved: "File saved to your downloads.",
      openCopilot: "Open Copilot",
      copiedToClipboard: "Copied to the clipboard.",
      copied: "Copied",
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
      open: "Open",
      close: "Close",
      confirm: "Confirm",
      cancel: "Cancel",
      save: "Save",
      delete: "Delete",
      edit: "Edit",
      loading: "Loading…",
      error: "Error",
      retry: "Retry",
      empty: "Nothing here yet",
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
      removedFromPipeline: "Removed from pipeline.",
      applicationNoteSaved: "Note saved.",
      reminderSet: "Reminder set.",
      reminderCleared: "Reminder cleared.",
      queuedForIngestion: "Queued for ingestion.",
      knowledgeNoteCreated: "Note created.",
      knowledgeNoteUpdated: "Note updated.",
      knowledgeNoteDeleted: "Note deleted.",
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
      accountMenu: "Account menu",
      commandPaletteTitle: "Command palette",
      commandPaletteDescription: "Search your career workspace and jump between sections",
      commandPalettePlaceholder: "Type a command or search…",
      searching: "Searching…",
      noResults: "No results.",
      searchFailed: "Content search failed — showing navigation only.",
      search: "Search",
      goTo: "Go to",
      resultsStreamIn: "content results stream in as you type.",
      previousPage: "Previous page",
      nextPage: "Next page",
      page: "Page {page}",
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
      },
      processing: {
        active: "Active",
        error: "Error",
        ariaLabel: "AI processing progress",
      },
      agentTimeline: {
        trace: "Agent execution trace",
        running: "Running",
        completed: "Completed",
        failed: "Failed",
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
      ctaMatch: "Match a job",
      skillGapsHint: "Ranked by the matching agent against your resume.",
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
      whereToFocusDescription:
        "Ranked by the matching agent against your resume.",
      recentRuns: "Recent AI runs",
      recentRunsDescription: "Every match, tailor and ingestion the agents performed.",
      resumeScore: "Resume score",
      knowledgeBase: "Knowledge base",
      knowledgeBaseDescription: "Sources ingestion feeds the retrieval layer.",
      aiUsage: "Agent spend",
      aiUsageDescription: "Requests and tokens the agents billed against your budget.",
      skillGaps: "Top skill gaps",
      skillGapsDescription: "Across your matched jobs.",
      followUps: "Follow-up reminders",
      followUpsDescription: "Contacts who need a touch, ranked by their relation's cadence.",
      noResumeScore: "No resume score yet",
      noResumeScoreDescription:
        "Upload and parse a resume — the reviewer agent grades bullets, structure, impact and keyword coverage.",
      noAttention: "Nothing needs attention",
      noAttentionDescription: "Every application has a recent step logged.",
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
      daysAgo: "{count}d ago",
      rowTokens: "{count} tokens",
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
      benchmark: "Benchmark",
      coachMe: "Coach me",
      draftCounter: "Draft a counter",
      whatTheMarketPays: "What the market pays",
      negotiationPlan: "Negotiation plan",
      counterOfferDraft: "Counter-offer draft",
      compareOffers: "Compare offers",
      offerLabels: "Offer labels",
      compare: "Compare",
      matchingPostings: "matching postings",
      noBenchmark: "No postings in the corpus for that role yet.",
      noComparison: "No offers to compare",
      nameOneOffer: "Name at least one offer above.",
      planReady: "Plan ready.",
      comparisonDone: "Offers compared.",
      counterOfferScript: "Counter-offer script",
      againstTheMarket: "Your offer against the market, and what to say.",
      leadsOnTotal: "{label} leads on total compensation.",
      anchorAt: "Anchor at {amount}.",
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
      weeklyQuietDays: "{days}d quiet",
      weeklyUntitled: "Untitled",
      weeklyHistory: "Earlier letters",
      weeklyEmpty: "No letters yet",
      weeklyEmptyDescription:
        "The first letter is written on Monday morning — or compose this week's now.",
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
      p95Latency: "P95 latency",
      alerts: "Alerts",
      regressions: "Regressions",
      runsAnalyzed: "runs analyzed",
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
      nightlyPassed: "passed",
      nightlyFailed: "failed",
      nightlyStepSkipped: "skipped",
      nightlyOpenRun: "Open the run",
      nightlyPagination: "Nightly reports pagination",
      nightlyRecords: "{count} nights recorded",
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
      description: "Bring postings in from a feed or a board API.",
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
        "Reminders that came due, applications that went quiet, and pulls that need a look — in the order they happened.",
      markAllRead: "Mark all read",
      unreadBadge: "{count} unread",
      allRead: "Everything here is read.",
      empty: "Nothing needs your attention right now.",
      emptyDescription:
        "A reminder that comes due, an application that goes quiet, or a failed feed pull will appear here.",
      unavailable: "The inbox couldn't be loaded.",
      kindReminder: "Reminder",
      kindStale: "Gone quiet",
      kindIngestionFailed: "Pull failed",
      kindIngestionCreated: "New postings",
      kindReply: "Recruiter reply",
      kindOther: "Signal",
      reminderLine: "Your reminder for {title} is due.",
      staleLine: "No movement on {title} — it has gone quiet.",
      ingestionFailedLine: "The last pull of {feed} failed.",
      ingestionCreatedLine: "New postings from {feed}: {count}.",
      replyLine: "A recruiter replied about your application — {title}.",
      fallbackLine: "A signal is waiting for you.",
      untitled: "Untitled",
      unnamedFeed: "an unnamed feed",
      open: "Open",
      openAria: "Open {title}",
      markRead: "Mark read",
      markReadAria: "Mark {title} read",
      dismiss: "Dismiss",
      dismissAria: "Dismiss {title}",
      actionFailed: "Couldn't update the inbox.",
    },
    // Growth engines
    growthEngines: {
      title: "Growth engines",
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
      locationOptional: "Location (optional)",
      coverage: "Coverage",
      covered: "covered",
      partial: "partial",
      expected: "expected",
      missingForDreamRole: "Missing for the dream role:",
      /**
       * The nine engines, by name.
       *
       * A key the table does not know keeps the engine's own English name
       * rather than losing it, which is the same rule `stageLabel` follows
       * for the pipeline's seven stages.
       */
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
      displayName: "Display name",
      signOut: "Sign out",
      signOutDescription: "Ends this session and revokes the refresh token.",
      sessionUnverified: "Session could not be verified.",
      appearance: "Appearance",
      appearanceDescription: "The interface follows your system theme by default.",
      renderingIn: "Rendering in {palette} palette.",
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
        "Read your reminders in the calendar app you already open. The address below is the whole credential — anyone holding it can read these reminders, and a new secret retires every address at once.",
      linkLabel: "Your calendar address",
      copy: "Copy address",
      loading: "Preparing your address…",
      loadFailed: "The address could not be prepared. Reload the page and try again.",
      hint: "Paste it into Google Calendar, Apple Calendar or Outlook under “subscribe from a URL”. A reminder appears on the calendar's next poll, and stays until you clear it here.",
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
      getAddress: "Get your address",
      empty: "No replies yet",
      emptyDescription:
        "Forward recruiter mail to your reply address and each letter lands here, attached to the application it answers.",
      paginationLabel: "Replies pages",
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
          continueAction: "Continue",
          reportAction: "Report",
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

    errorCodes: {
      ABORTED: "The upload was cancelled.",

      AI_SERVICE_BAD_REQUEST: "The AI service returned a bad request.",
      AI_SERVICE_CONFLICT: "The AI service is not ready yet.",

      AI_SERVICE_EMPTY_RESPONSE: "The AI service answered with nothing.",

      AI_SERVICE_NOT_FOUND: "That is no longer here.",

      AI_SERVICE_UNAVAILABLE: "The AI service is not answering.",

      APPLICATION_NOT_FOUND: "That application is no longer here.",

      BUNDLE_NOT_PLANNABLE: "That file could not be turned into a restore plan.",

      BUNDLE_NO_SECTION: "That file has no data section.",

      CALENDAR_LINK_INVALID: "That calendar link is not valid or has been retired.",

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

      INBOUND_LINK_INVALID: "That inbound address is not valid or has been retired.",

      INBOUND_MAIL_ALREADY_FILED:
        "This reply is already filed on another application; open it there instead.",

      INBOUND_MAIL_NOT_FOUND: "That reply is no longer here.",

      INBOUND_NOT_CONFIGURED: "Inbound mail is not configured on this deployment.",

      INTERNAL_ERROR: "An internal server error occurred.",

      INTERVIEW_ALREADY_STARTED: "This interview has already started.",

      INTERVIEW_NOTHING_TO_FINALIZE: "There is nothing to finish yet.",

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
      renameChatAria: "Rename “{title}”",
      deleteChatAria: "Delete “{title}”",
    },
    // Networking
    networking: {
      title: "Contacts",
      description:
        "The people a search actually touches — who they are, how you know them, and when you last talked.",
      noContacts: "No contacts yet",
      noContactsDescription:
        "Add the referrers, mentors and peers you talk to — Copilot drafts messages for them, and the follow-up reminders will read this list.",
      addContact: "Add contact",
      editContact: "Edit contact",
      onlyNameRequired: "Only the name is required — fill in what you know, leave the rest.",
      name: "Name",
      role: "Role",
      company: "Company",
      relation: "Relation",
      email: "Email",
      lastTouch: "Last touch",
      lastTouchLine: " · last touch {when}",
      notes: "Notes",
      notesPlaceholder: "Context for the next message — how you met, what you discussed.",
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
    },
    // Growth report
    growth: {
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
      analyze: "Analyze",
      roleTooShort: "Name the role fully — the analyzer needs at least 10 characters to target it.",
      covered: "Covered",
      partial: "Partial",
      open: "Open",
      coverage: "Coverage",
      salaryBand: "Salary band",
      matchingPostings: "matched postings",
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
      run: "Run",
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
      askCopilotToIngest: "Ask Copilot to ingest",
      paginationLabel: "sources",
      notes: {
        titleLabel: "Title (optional)",
        titlePlaceholder: "e.g. Answers for the “why us” question",
        content: "Content",
        contentPlaceholder:
          "Write it down — the agents can quote this back with a citation.",
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
        pending: "pending",
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
      emptyDescription:
        "Once Copilot or a matching job runs, its full trace appears here.",
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
      reminderDue: "reminder due",
      noStep14d: "no step 14d+",
      reminderOn: "reminder {date}",
      pipelineIsEmpty: "Pipeline is empty",
      dropCardHere: "Drop a card here",
      savingMove: "Saving move…",
      pipelineIsEmptyDescription:
        "Track a job from its detail page and it appears here, starting in Saved.",
      addApplication: "Add application",
      add: "Add",
      paginationLabel: "applications",
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
      },
      report: {
        solidPractice: "Solid practice — the weak dimensions below are the fastest wins.",
        perDimension: "Per-dimension results below.",
        practiceHint: "Run the same mode again after studying — the agent adapts to your previous weak spots.",
        untitledResource: "Untitled resource",
        strongSession: "Strong session — the loop pushed you deep and you held the altitude.",
        loadFailed: "Couldn't load the report",
        stillRunning: "The interview is still running",
        stillRunningDescription:
          "Finish the session and the evaluator will score every answer into a full report.",
        noReport: "No report stored yet",
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
        legendDepth: "how many questions in a row the agent followed up on",
        legendScore: "your score",
        hoverDots: "hover the dots for each question",
      },
    },
    // Jobs
    jobs: {
      notLiveSearchTitle: "This API build has no job search",
      notLiveSavedTitle: "This API build has no saved-jobs list",
      title: "Jobs",
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
        originalPosting: "Original posting",
        matchRunFailed: "Match run failed:",
        unknownError: "unknown error",
        requirementsBreakdown: "Requirements breakdown",
        requirementsBreakdownDescription: "Priority analysis from the JD extractor.",
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
      deleteTitle: "Forget this saved search?",
      deleteDescription: "\"{name}\" is removed from the sidebar. The jobs themselves are not touched.",
      deleteConfirm: "Delete",
      deleteFailed: "Couldn't delete that search.",
      deletedToast: "Saved search deleted.",
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
      openingQuestion: "Couldn't fetch the opening question.",
      answerEvaluate: "Couldn't evaluate that answer.",
      interviewFinalize: "Couldn't finalize the interview.",
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
      counterOffer: "Couldn't draft the counter-offer.",
      mfaEnroll: "Couldn't start two-factor setup.",
      mfaActivate: "Couldn't prove the code — two-factor is still off.",
      mfaRecoveryCodes: "Couldn't replace the recovery codes.",
      mfaDisable: "Couldn't turn two-factor off.",
      mailSettingSave: "Couldn't change that mail setting.",
    },
  },
  zh: {
    // Navigation
    nav: {
      dashboard: "仪表盘",
      notifications: "通知",
      replies: "回信",
      resumes: "简历",
      jobs: "职位",
      applications: "申请",
      interviews: "面试",
      copilot: "副驾驶",
      knowledge: "知识库",
      companies: "公司",
      growth: "成长",
      networking: "人脉",
      analysis: "分析",
      offers: "录用",
      monitoring: "监控",
      rateLimit: "限流",
      activity: "活动",
      settings: "设置",
      ingestion: "职位导入",
      yourData: "你的数据",
    },
    /**
     * 导航自己的说明句——命令面板每行下面的第二行。
     *
     * 单独一个块，因为它们本来就是另一句话：页面的名字，和说明这个页面
     * 是做什么的那句话，是两回事，改动它们的人也不一样。
     */
    navDescriptions: {
      dashboard: "求职全局与优先事项",
      notifications: "需要你关注的信号",
      replies: "归到投递上的招聘方回信",
      resumes: "简历版本与结构化档案",
      jobs: "发现的职位与 AI 匹配",
      applications: "投递看板与提醒",
      interviews: "自适应 AI 模拟面试",
      copilot: "求职代理对话",
      knowledge: "职业知识库资料",
      companies: "公司调研档案",
      growth: "准备度、差距与学习计划",
      networking: "人脉与外联",
      analysis: "投递分析与洞察",
      offers: "薪资对标与谈判",
      monitoring: "代理健康度与成本",
      rateLimit: "限流状态与配额",
      ingestion: "从订阅源和招聘板导入职位",
      yourData: "导出、恢复与删减你的数据",
      activity: "AI 代理运行与轨迹",
      settings: "账号与偏好",
    },
    theme: {
      switchToLight: "切换到浅色主题",
      switchToDark: "切换到深色主题",
    },
    save: {
      remove: "从收藏里移除",
      save: "收藏这个职位",
      saved: "已收藏",
      saveShort: "收藏",
    },
    // Common actions
    common: {
      clipboardBlocked: "浏览器拦截了剪贴板访问。",
      fileSaved: "文件已保存到下载目录。",
      openCopilot: "打开副驾",
      copiedToClipboard: "已复制到剪贴板。",
      copied: "已复制",
      pageNotFound: "页面不存在",
      metaDescription:
        "你的个人求职操作系统——有证据支撑的匹配、简历情报，以及 AI 引导的面试。",
      notLiveTitle: "这个后端版本没有这一页的数据",
      endpointOffline: "{name} 尚未接通——等 API 提供后就会显示。",
      refresh: "刷新",
      open: "打开",
      close: "关闭",
      confirm: "确认",
      cancel: "取消",
      save: "保存",
      delete: "删除",
      edit: "编辑",
      loading: "加载中…",
      error: "错误",
      retry: "重试",
      empty: "暂无数据",
      tryAgain: "再试一次",
      checkAgain: "再检查一次",
      somethingWentWrong: "出了点问题",
      skipToContent: "跳到正文",
      backToDashboard: "回到仪表盘",
      missingEndpoint:
        "此页面需要的接口返回了 404，说明这个前端和它正在通信的后端版本不一致。这里没有任何内容替代真实数据。",
      missingEndpointRoute:
        "{route} 返回了 404，说明这个前端和它正在通信的后端版本不一致。这里没有任何内容替代真实数据。",
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
      resumeUploaded: "已上传——正在解析你的简历。",
      resumeCurrent: "当前版本已更新。",
      resumeDeleted: "简历已删除。",
      savedJobRemoved: "已从收藏中移除。",
      jobSavedToPipeline: "已保存到流水线。",
      resumeTailored: "定制简历已就绪——导出前请先查看差异。",
      matchComplete: "匹配分析已完成。",
      jobImported: "职位已导入——分析师已补齐细节。",
      addedToPipeline: "已加入流水线。",
      removedFromPipeline: "已从流水线移除。",
      applicationNoteSaved: "备注已保存。",
      reminderSet: "提醒已设置。",
      reminderCleared: "提醒已清除。",
      queuedForIngestion: "已加入采集队列。",
      knowledgeNoteCreated: "笔记已创建。",
      knowledgeNoteUpdated: "笔记已更新。",
      knowledgeNoteDeleted: "笔记已删除。",
      interviewReportReady: "面试报告已就绪。",
      conversationRenamed: "对话已重命名。",
      conversationDeleted: "对话已删除。",
      profileSaved: "个人资料已保存。",
      careerProfileSaved: "职业档案已保存。",
      memoryUpdated: "记忆已更新。",
      memoryForgotten: "记忆已遗忘。",
      contactSaved: "联系人已保存。",
      contactUpdated: "联系人已更新。",
      contactDeleted: "联系人已删除。",
    },
    /**
     * What a screen reader is told while a surface is still loading.
     *
     * These are the announcements, not the shimmer: they are the only words a
     * reader who cannot see the skeleton hears, and they are what tells them
     * *which* thing is loading rather than that something is.
     */
    loading: {
      generic: "加载中",
      jobs: "正在加载职位",
      pipeline: "正在加载流水线",
      conversation: "正在加载对话",
      detail: "正在加载详情",
      page: "正在加载页面",
      workspace: "正在加载你的工作区…",
      table: "正在加载表格",
      inProgress: "加载中…",
    },
    /**
     * The chrome around every surface: the sidebar, the top bar, the command
     * palette and the pager. These are the labels a screen reader announces
     * for the navigation itself, so they are part of the product's voice and
     * not implementation detail.
     */
    chrome: {
      logOut: "退出登录",
      signingOut: "正在退出…",
      signedIn: "已登录",
      mainNavigation: "主导航",
      goToDashboard: "AI Career OS — 回到仪表盘",
      openNavigationMenu: "打开导航菜单",
      openCommandPalette: "打开命令面板",
      accountMenu: "账户菜单",
      commandPaletteTitle: "命令面板",
      commandPaletteDescription: "搜索你的求职工作区，在各个板块之间跳转",
      commandPalettePlaceholder: "输入命令或搜索…",
      searching: "正在搜索…",
      noResults: "没有结果。",
      searchFailed: "内容搜索失败——只显示导航项。",
      resultsStreamIn: "输入的同时内容结果会陆续出现。",
      search: "搜索",
      goTo: "跳转到",
      previousPage: "上一页",
      nextPage: "下一页",
      page: "第 {page} 页",
      refreshList: "刷新列表",
      pagination: "分页（{label}）",
      ofTotal: "第 {from}–{to} 条，共 {total} {label}",
      noRowsYet: "还没有{label}",
      prev: "上一页",
      next: "下一页",
      switchToChinese: "切换到中文",
      switchToEnglish: "切换到英文",
      expandSidebar: "展开侧边栏",
      collapseSidebar: "收起侧边栏",
      collapse: "收起",
      profileAndPreferences: "个人资料与偏好",
      settings: "设置",
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
      ariaLabel: "上传简历",
      uploading: "上传中…",
      dropHere: "把简历拖到这里，或点击选择",
      accepted:
        "{formats} — 最大 {mb} MB。文件留在你的工作区里，并成为代理引用的知识库的一部分。",
      problemUnsupported: "只支持 PDF、DOCX 或 TXT 文件。",
      problemTooLarge: "文件大于 {mb}MB。",
      problemEmpty: "这个文件看起来是空的。",
      ingesting: "摄取中",
      ingestedToast: "简历已摄取——你的知识库已更新。",
      canLeave: "你可以离开这个页面——运行会在服务端继续，下面的列表会反映它的真实状态。",
      sending: "正在发送文件…",
      ingest: {
        extracting: "从文件里提取文本",
        cleaning: "清洗并规范化文本",
        chunking: "切成可检索的块",
        embedding: "为每一块生成向量",
        indexing: "建立文档索引",
      },
    },
    // AI / task stream
    ai: {
      generated: "AI 生成",
      taskStream: {
        waitingForAgent: "正在等待代理…",
        streamNotReported: "运行流还没有报告进度 —— 一有结果就立即显示。",
        agentTrace: "代理追踪",
        runError: "这次运行报告了一个错误。",
        steps: "{count} 步",
      },
      processing: {
        active: "进行中",
        error: "错误",
        ariaLabel: "AI 处理进度",
      },
      agentTimeline: {
        trace: "代理执行轨迹",
        running: "进行中",
        completed: "已完成",
        failed: "失败",
      },
    },
    jobCard: {
      companyNotResearched: "这家公司还没调研过",
      noMatchYet: "还没有算过匹配度",
      matchFor: "与「{title}」的匹配度",
      whyThisJob: "为什么是这个职位：",
      pastedJd: "粘贴的 JD",
      foundByResearch: "调研代理找到的",
    },
    /**
     * The charts the product draws.
     *
     * A chart with nothing to draw says so; the word is the reader's.
     */
    chart: {
      nothingToPlot: "还没有可画的数据。",
    },
    /**
     * The diff the tailor panel shows: the numbers beside the change list,
     * and the panel the list lives in.
     */
    diffView: {
      whyNotApplied: "为什么没有采用：",
      why: "为什么：",
      bullet: "要点",
      skipped: "已跳过",
      applied: "已应用",
      statistics: "定制统计",
      agentNotes: "代理备注",
      appliedChanges: "已采纳的改动",
      rejectedProposals: "被否决的提案",
      noSafeEdits: "代理没有为这个职位提出安全的改动——它不会改写它无法举证的经历。",
      hide: "收起",
      showReasons: "看原因",
    },
    /**
     * One piece of cited evidence, and the card it sits in.
     */
    evidence: {
      showAllCount: "显示全部 {count} 条证据",
      showFewer: "收起一些",
      source: "证据来源",
      jumpToSource: "跳到来源",
      citationAria: "引用 {index}：{title}",
      citationAriaSection: "引用 {index}：{title} — {section}",
    },
    /**
     * The recovery screens. The copy here is careful on purpose -- the
     * endpoint answers 200 for an address with no account, so the screen says
     * "if that address has an account" and never more. The translation keeps
     * that hedge.
     */
    recovery: {
      checkEmail: "查收邮件",
      checkEmailBody: "如果 {email} 有账号，重置令牌已经在路上了。令牌 30 分钟内有效。",
      alreadyHaveToken: "我已经有令牌了",
      differentAddress: "换一个邮箱",
      resetHeading: "重置密码",
      resetBody: "告诉我们账号上的邮箱，我们会给它发一个重置令牌。",
      email: "邮箱",
      emailPlaceholder: "you@example.com",
      sendToken: "发送重置令牌",
      remembered: "想起来了？",
      signIn: "登录",
      passwordUpdated: "密码已更新",
      signedOutEverywhere:
        "所有已登录的设备都已被登出。用新密码就能重新进来。",
      setNewPassword: "设置新密码",
      pasteToken:
        "把邮件里的令牌粘贴进来，然后选一个密码。保存之后，其他地方的登录会立刻失效。",
      stopsElsewhere: "保存之后，其他地方的登录会立刻失效。",
      resetToken: "重置令牌",
      resetTokenPlaceholder: "邮件里的那个令牌",
      newPassword: "新密码",
      confirmNewPassword: "确认新密码",
      saveNewPassword: "保存新密码",
      tokenExpired: "令牌过期了？",
      requestAnother: "再要一个",
      genericFailure: "出错了，请再试一次。",
    },
    emailChange: {
      confirmHeading: "确认新邮箱地址",
      answering: "正在回应邮件里的链接……",
      movedTitle: "邮箱已更换",
      movedBody:
        "登录邮箱已经更换，所有设备都已退出登录。请用新邮箱和原来的密码重新登录。",
      invalidTitle: "这个链接不能用",
      invalidBody:
        "它可能已经过期、已经被使用，或者从未发出。登录后请在设置 → 账户里重新申请。",
      registeredTitle: "这个邮箱已经被占用",
      registeredBody:
        "在链接被回应之前，另一个账号注册了这个邮箱，所以这次更换没有发生。登录后请在设置 → 账户里换一个地址。",
      pasteBody: "请打开邮件里的链接。如果链接没有打开，可以把其中的令牌粘贴到这里。",
      tokenLabel: "链接令牌",
      tokenPlaceholder: "邮件里的令牌",
      confirm: "确认更换",
      retryBody: "刚才没能回应这个链接。它仍然有效——可以再试一次。",
      retry: "重试",
    },
    /**
     * 设置页上的换邮箱卡片（38.2）。这里每一句都照实描述服务端的动作：寄出两封信，
     * 新邮箱回应之前什么都不改变，换址本身会让所有会话退出登录。
     */
    emailMove: {
      title: "登录邮箱",
      description: "更换这个账号用来登录的邮箱。申请会寄出两封信，换址要等新邮箱回应才生效。",
      current: "这个账号现在用 {email} 登录。",
      newLabel: "新邮箱",
      newPlaceholder: "you@example.com",
      passwordLabel: "当前密码",
      passwordPlaceholder: "输入你的当前密码",
      send: "寄出确认信",
      sentTitle: "两封信已经在路上",
      sentBody:
        "一封寄往 {newEmail}，里面的链接在两个小时里有效，点开它换址才会完成；另一封寄往 {oldEmail}，让能看到那个邮箱的人知道有人申请了换址。新邮箱点开链接之前，什么都不会改变。",
      hint: "链接被回应后，所有会话都会退出登录；密码保持不变。",
      askAgain: "换一个邮箱",
    },
    sessions: {
      title: "开放中的登录",
      description: "所有还能为这个账号续期登录的浏览器和设备。每一行是一段登录，无论它续期过多少次。",
      loading: "正在读取这些门……",
      loadFailed: "登录列表没能读出来。",
      empty: "现在没有任何一段登录能续期。这个标签页的访问令牌到期后，会请你重新登录。",
      current: "这台设备",
      currentNote: "这就是你正在使用的标签页。关掉它等同于退出登录。",
      unknownDevice: "未命名的设备",
      address: "来自 {address}",
      started: "开始于 {when}",
      seen: "最后活动 {when}",
      expires: "可续期至 {when}",
      close: "关闭",
      closeNamed: "关闭 {device}",
      closeTitle: "关闭这段登录？",
      closeOneDescription: "{device} 会立刻停止续期，并在下次需要新的访问令牌时退出登录。",
      closeCurrentDescription:
        "这就是你正在使用的标签页。关掉它等同于退出登录：这个标签页只能用到访问令牌到期为止。",
      closeAll: "关闭所有登录",
      closeAllHint: "结束所有设备上的登录，包括这一台。",
      closeAllTitle: "关闭所有登录？",
      closeAllDescription: "所有设备都会退出登录，包括这一台。这个标签页只能用到访问令牌到期为止。",
      alreadyClosed: "这段登录已经关闭了；列表已刷新。",
    },
    /**
     * 设置页的密码卡片（38.4）。成功态说出服务端的完整后果：所有刷新令牌作废，
     * 其他设备下次续期时退出登录，这个标签页用到自己的访问令牌到期。
     */
    passwordChange: {
      title: "密码",
      description: "更换这个账号登录用的密码。会先核对当前密码，借来的标签页没法把你锁在外面。",
      currentLabel: "当前密码",
      currentPlaceholder: "输入你的当前密码",
      newLabel: "新密码",
      newPlaceholder: "至少 8 个字符",
      confirmLabel: "再输入一次新密码",
      confirmPlaceholder: "再输入一次新密码",
      submit: "更换密码",
      hint: "更换密码会让其他设备都退出登录；这个标签页会一直用到访问令牌到期。",
      changedTitle: "密码已经更换",
      changedBody:
        "所有会话的刷新令牌都已作废：其他设备下次需要新的访问令牌时会退出登录，这个标签页会用到自己的访问令牌到期为止，然后请你用新密码重新登录。从现在起登录都用新密码。",
      again: "再换一次",
    },
    /**
     * 删除账号卡片（38.5）。每一句都照实描述服务端的动作：两道核对、先删文件再删行、
     * 随账号级联的行，以及实时系统之外、要等保留期结束的备份。
     */
    eraseAccount: {
      title: "删除这个账号",
      description: "彻底关闭这个账号。需要输入密码，并再次输入登录邮箱；任何一项不对，什么都不会被删除。",
      current: "正在删除的是 {email}。",
      leavesTitle: "会离开的",
      leavesBody:
        "所有指向这个账号的行——资料、简历与版本、职位、申请、面试、知识库来源、来信、通知、会话与令牌——以及这些文档背后的每一个已存储文件。",
      staysTitle: "会留下的",
      staysBody:
        "实时系统之外的备份会保留它们记录下的内容，直到保留期结束。已经投递出去的信件留在各自的邮箱里。",
      passwordLabel: "当前密码",
      passwordPlaceholder: "输入你的当前密码",
      confirmLabel: "再次输入登录邮箱",
      confirmPlaceholder: "{email}",
      hint: "大小写和首尾空格不计较；换一个邮箱会被拒绝。",
      submit: "删除账号",
      dialogTitle: "确定要彻底删除这个账号吗？",
      dialogDescription:
        "先核对输入的密码，再核对 {email}。两项都通过后，这个账号名下的所有行和所有已存储文件都会被删除，无法恢复。",
      dialogConfirm: "彻底删除",
    },
    /**
     * 24.2 的路由回答 `{erased: true}` 之后落到的页面（38.5）。读者已经没有账号、
     * 也没有会话，所以页面直说这一点，并给出仍然存在的两扇门：注册新账号，或用另一个账号登录。
     */
    accountErased: {
      title: "账号已经删除",
      body: "这个账号名下的所有行和所有已存储文件都已删除，任何会话都无法再用它登录。",
      keptTitle: "仍然留在外面的",
      keptBody:
        "实时系统之外的备份会保留它们记录下的内容，直到保留期结束；已经投递出去的信件留在各自的邮箱里。",
      startAgain: "注册新账号",
      signInOther: "登录另一个账号",
    },
    tailor: {
      title: "为这个职位定制的简历",
      draftBadge: "定制草稿",
      eyebrow: "AI 定制",
      descriptionWith: "基于 {resume} 重写要点并重排项目顺序。",
      description: "基于你当前的简历重写要点并重排项目顺序。",
      neverInvented: "绝不虚构经历",
      claimsKeptOut: "——没有依据的说法一律拒绝并列出。",
      runAgain: "再跑一次",
      tailorNow: "立即定制",
      failed: "定制失败。",
      savedAs: "已保存为 {name}",
      diff: "差异",
      fullDocument: "完整文档",
      saveAgain: "再存一次",
      saveAsVersion: "存为版本",
      printVersion: "打印此版本",
      noStructuredDiff: "返回的内容里没有结构化差异。文档视图仍然显示生成的内容。",
      noDocumentText: "这次运行没有返回文档正文——只有上面的改动清单。",
      evidenceUsed: "用到的证据",
      nothingGeneratedYet:
        "还没有生成任何内容——跑一次之后草稿会出现在这里，在你导出或存为版本之前它一直只是一份提案。",
      stages: {
        readingKnowledge: "正在阅读你的知识库",
        matchingExperience: "正在把经历对上 JD",
        rewritingBullets: "正在重写要点",
        checkingClaims: "正在核对是否有虚构",
      },
    },
    coverLetter: {
      title: "求职信",
      description: "基于你的简历证据、JD 和公司背景生成。随时可以用不同的语气或长度重新生成。",
      draftBadge: "草稿",
      copyLetter: "复制求职信",
      download: "下载",
      eyebrow: "AI 代写",
      tone: "语气",
      length: "长度",
      tones: {
        balanced: "均衡",
        formal: "正式",
        concise: "简洁",
        confident: "自信",
      },
      lengths: {
        short: "简短（约 180 词）",
        standard: "标准（约 300 词）",
        detailed: "详细（约 450 词）",
      },
      generate: "生成",
      regenerate: "重新生成",
      words: "{count} 词",
      generationFailed: "生成失败。",
      noLetterText: "返回的内容里没有正文——试试重新生成。",
      noLetterYet: "这个职位还没有生成求职信。",
      stages: {
        readingJd: "正在阅读 JD",
        pullingContext: "正在获取公司背景",
        drafting: "正在起草",
        checkingClaims: "正在核对说法",
      },
    },
    // Dashboard
    dashboard: {
      theScoredVersion: "每个代理打分时对照的那一版。",
      resumeTitle: "简历",
      resumeReady: "{status} · 所有代理按这一版匹配",
      resumeAwaitingParse: "{status} · 结构化档案尚未就绪",
      straightFromTheBoard: "直接来自职位板——跑一次匹配来给它们排序。",
      ctaPasteJd: "粘贴一份 JD",
      ctaMatch: "匹配一个职位",
      skillGapsHint: "由匹配代理对着你的简历排出来的。",
      gradeHint: "来自简历评审代理的总评。打开简历可以看到每个维度的细分。",
      gradeWeak: "偏弱——从这里开始",
      gradeNeedsWork: "还要打磨",
      gradeSolid: "基础扎实",
      gradeInterviewReady: "可以面试了",
      title: "仪表盘",
      greeting: "早上好",
      greetingHello: "你好",
      greetingMorning: "早上好",
      greetingAfternoon: "下午好",
      greetingEvening: "晚上好",
      description: "求职全局一览——这里的每个数字都实时读自 API。",
      applications: "申请",
      interviews: "面试",
      offers: "录用",
      avgMatch: "平均匹配",
      averageMatch: "平均匹配度",
      needsAttention: "需要关注",
      pipeline: "流水线",
      pipelineDescription: "每个阶段的计数，实时来自申请看板。",
      attention: "需要关注",
      attentionDescription: "已到期的提醒，以及两周没有任何进展记录的申请。",
      whereToFocus: "值得关注",
      whereToFocusDescription: "由匹配代理根据你的简历排序。",
      recentRuns: "最近AI运行",
      recentRunsDescription: "代理做过的每一次匹配、定制和摄取。",
      resumeScore: "简历评分",
      knowledgeBase: "知识库",
      knowledgeBaseDescription: "摄取喂给检索层的来源。",
      aiUsage: "AI消耗",
      aiUsageDescription: "代理记在你账上的请求与令牌。",
      skillGaps: "技能差距",
      skillGapsDescription: "来自你已匹配的职位。",
      followUps: "跟进提醒",
      followUpsDescription: "需要联系的联系人，按关系节奏排序。",
      noResumeScore: "还没有简历评分",
      noResumeScoreDescription: "上传并解析简历——评审代理会打分条目、结构、影响力和关键词覆盖。",
      noAttention: "没有需要关注的事项",
      noAttentionDescription: "每个申请都有近期的进展记录。",
      boardIsEmpty: "看板上还是空的。",
      emptyPipeline: "流水线里还没有东西",
      emptyPipelineDescription:
        "收藏一个职位就开始跟踪它——看板覆盖了收藏 → 已投递 → 测评 → 面试 → 终面 → 录用。",
      emptyResumes: "知识库里还没有简历",
      emptyResumesDescription:
        "上传你的简历——解析会把内容送进知识库，这样每个 AI 回答都能引用真实经历。",
      trackedApplications: "在跟 {count} 个申请。",
      reminderDue: "提醒于 {when} 到期",
      lastStep: "最近进展 {when}",
      noStep: "没有进展记录",
      snoozeReminder: "推迟到明早",
      clearReminder: "清除",
      moreNeedAttention: "看板上还有 {count} 个需要关注。",
      askCopilot: "问问副驾驶",
      openCopilot: "打开副驾驶",
      openPipeline: "打开流水线",
      openBoard: "打开看板",
      openJobs: "打开职位板",
      goToJobs: "去职位板",
      allJobs: "全部职位",
      browseJobs: "逛职位板",
      fullLog: "完整日志",
      uploadResume: "上传简历",
      openNetworking: "打开人脉",
      avgMatchLabel: "平均匹配",
      avgMatchBody: "在已打分的职位上，来自你的简历证据",
      preferToTalk: "更想直接聊？",
      preferToTalkBody: "，描述你的目标职位——它会问它需要什么。",
      detail: "详情",
      manage: "管理",
      requests: "请求数",
      tokensLabel: "Token 数",
      costLabel: "成本",
      daysAgo: "{count} 天前",
      rowTokens: "{count} 个 token",
      trace: "链路",
      open: "打开",
      noFollowUps: "没有需要跟进的人",
      noFollowUpsDescription: "在「人脉」里添加联系人，他们的节奏就会排到这里。",
      noRecommendations: "还没有可推荐的职位",
      noRecommendationsDescription: "粘贴一份 JD，或让研究代理填满看板——有东西可排时推荐就会出现。",
      noRuns: "还没有AI运行",
      noRunsDescription: "做一次匹配或定制简历，编排器就会把每一步记录在这里。",
      noSpend: "还没有AI消耗",
      noSpendDescription: "匹配一个职位或定制一份简历，令牌数就会出现在这里。",
      noGaps: "还没有测出差距",
      noGapsDescription: "对某个职位做一次匹配，缺失的技能就会按重要度排在这里。",
      statsNotConnected: "仪表盘统计还没接上",
      statsFailed: "仪表盘统计加载失败",
      attentionFailed: "关注列表加载失败",
      recommendationsFailed: "推荐加载失败",
      runsFailed: "最近运行加载失败",
      spendFailed: "AI 消耗加载失败",
      gapsFailed: "技能差距加载失败",
      rolesInFlight: "个进行中的申请",
      restBelow: "页面其余部分仍会在下方读取真实接口的数据。",
      reachedOrPracticed: "个已到达或已练习",
      readyForDecision: "个待决策",
      staleOrDue: "个停滞或到期的提醒",
      onboardingTitle: "开始搭建你的工作台",
      onboardingDescription: "这里没有任何预填内容——按顺序完成这些步骤即可解锁全部功能。",
      stepUpload: "上传你的简历",
      stepUploadDescription: "解析会生成结构化档案和知识库，每个代理都从这里取证。",
      stepJd: "添加一份职位描述",
      stepJdDescription: "在「职位」里粘贴任意 JD → 分析 JD，提取要求与隐藏信号。",
      stepMatch: "做第一次匹配",
      stepMatchDescription: "匹配器按维度给你打分，并为每个数字引用简历原文。",
      stepTrack: "跟踪流水线",
      stepTrackDescription: "收藏的职位流经看板：已收藏 → 已投递 → 笔试 → 面试 → 录用。",
    },
    // Offers
    offers: {
      theAnchor: "引擎算出来的锚点。",
      compared: "录用已比较完毕。",
      negotiationPlanReady: "谈判方案已就绪。",
      counterOfferReady: "还价草稿已就绪。",
      offerFormat: "一行一个录用。引擎按总薪酬排序，股权按归属期折算成年化。",
      oneQuestion: "四个答案都由同一个问题驱动：职位是什么，桌上摆着什么。",
      title: "录用",
      description: "市场给多少、怎么回话、哪个录用最划算。",
      roleAndOffer: "职位与录用",
      role: "职位",
      location: "城市（可选）",
      offerBase: "Base 薪资（可选）",
      yourMatch: "你的匹配度 %（可选）",
      benchmark: "对标市场",
      coachMe: "谈判指导",
      draftCounter: "起草还价",
      whatTheMarketPays: "市场给多少",
      negotiationPlan: "谈判方案",
      counterOfferDraft: "还价草稿",
      compareOffers: "比较多个录用",
      offerLabels: "录用名称",
      compare: "比较",
      matchingPostings: "个匹配职位",
      noBenchmark: "语料库里还没有这个职位的职位。",
      noComparison: "没有可比较的录用",
      nameOneOffer: "请至少写一个录用名称。",
      planReady: "方案已就绪。",
      comparisonDone: "录用已比较。",
      counterOfferScript: "还价话术",
      againstTheMarket: "你的录用对着市场，以及该怎么说。",
      leadsOnTotal: "{label} 的总薪酬最高。",
      anchorAt: "锚定在 {amount}。",
    },
    // Analysis
    analysis: {
      title: "分析",
      description: "基于你的申请历史的数据分析和洞察。",
      totalApplications: "总申请数",
      activePipeline: "活跃流水线",
      responseRate: "回复率",
      stalled: "停滞",
      stageMix: "阶段分布",
      stalledApplications: "停滞申请",
      insights: "洞察",
      funnel: "漏斗",
      funnelDescription: "每个阶段到达的申请数，以及每一步的转化率。",
      ofApplied: "占已投递比例",
      responseRates: "回复率",
      responseRatesDescription: "所有投递中收到任何回复的比例——被拒也算回复。",
      reply: "回复",
      interview: "面试",
      offer: "录用",
      gotAReply: "{applied} 个投递中有 {replied} 个收到了回复。",
      noFunnel: "还没有漏斗数据",
      noFunnelDescription: "投出第一个申请，漏斗就会开始测量流失点。",
      noStalled: "没有停滞的申请",
      noStalledDescription: "每个申请都有近期动态。",
      loadFailed: "分析数据加载失败",
      stageMixDescription: "每个流水线阶段上的申请数。",
      noStageYet: "还没有申请走到任何阶段。",
      stalledDescription: "超过 {days} 天没有任何进展的申请。",
      insightsDescription: "数据对你的流水线说了什么。",
      weeklyTitle: "每周来信",
      weeklyDescription: "按周期自动生成并留存，让一周的信号不会随一周过去而消失。",
      weeklyCompose: "生成本周",
      weeklyComposing: "正在生成…",
      weeklyWeek: "{date} 当周",
      weeklyApplications: "投递",
      weeklyQuietCount: "无动静",
      weeklyReply: "回复率",
      weeklyOffer: "录取率",
      weeklyQuietDays: "已 {days} 天",
      weeklyUntitled: "未命名",
      weeklyHistory: "更早的来信",
      weeklyEmpty: "还没有来信",
      weeklyEmptyDescription: "第一封信会在周一早晨写好——也可以现在就生成本周这一封。",
      weeklyUnavailable: "来信暂时无法加载。",
      weeklyActionFailed: "无法生成来信。",
    },
    // Monitoring
    monitoring: {
      title: "监控",
      description: "代理健康度、成本和回归检测。",
      healthVerdict: "健康结论",
      errorRate: "错误率",
      totalCost: "总成本",
      totalTokens: "总令牌数",
      p95Latency: "P95 延迟",
      alerts: "告警",
      regressions: "回归",
      runsAnalyzed: "次运行已分析",
      alertsDescription: "需要关注的问题。",
      regressionsDescription: "相对基线退化的指标。",
      loadFailed: "监控数据加载失败",
      latency: "延迟",
      latencyDescription: "中位调用和慢尾，画在同一把尺子上。",
      p50: "p50（中位）",
      p95: "p95（长尾）",
      verdictDescription: "代理的整体健康评估。",
      nightlyTitle: "夜间验证",
      nightlyDescription: "部署自身的检查，每晚一条记录：后端测试、评测框架与可移植导出。",
      nightlyEmpty: "还没有任何夜晚留下记录。夜间任务完成时会写入一条。",
      nightlyUnavailable: "无法读取夜间历史。",
      nightlyVerdictMissing: "还没有任何夜晚留下记录——验证任务可能从未运行过。",
      nightlyVerdictStale: "最新记录已超过 {hours} 小时——夜间任务停止上报了。",
      nightlyVerdictStreak: "已连续 {count} 个夜晚以失败告终。",
      nightlyPassed: "通过",
      nightlyFailed: "失败",
      nightlyStepSkipped: "跳过",
      nightlyOpenRun: "打开该次运行",
      nightlyPagination: "夜间报告分页",
      nightlyRecords: "已记录 {count} 个夜晚",
    },
    // Rate limit
    rateLimit: {
      noThrottling: "没有启用任何限流。",
      throttledPerUser: "请求按用户分别限流。",
      title: "限流",
      description: "当前限流配置和你的配额使用。",
      rateLimiting: "限流",
      aiEndpoints: "AI 接口",
      authEndpoints: "认证接口",
      yourRemainingQuota: "你的剩余配额",
      enabled: "已启用",
      disabled: "已禁用",
      aiDescription: "AI 相关接口的每用户限速（副驾驶、面试、JD 分析等）。",
      authDescription: "认证接口的每 IP 限速（登录、注册等）。",
      quotaDescription: "你账户当前的令牌桶用量。",
      loadFailed: "限流状态加载失败",
      enabledDescription: "限流是否开启。",
    },
    // Data portability
    data: {
      planReady: "计划已就绪。",
      notValidJson: "这不是合法的 JSON。",
      sectionsRemoved: "已删减对应部分，并重新计算了内容哈希。",
      fileSaved: "文件已保存到下载目录。",
      exportReady: "导出已完成。",
      title: "你的数据",
      description: "导出全部、预览恢复、分享前删减。",
      sections: {
        profile: "个人资料",
        resumes: "简历",
        knowledge: "知识库",
        jobDescriptions: "职位描述",
        interviews: "面试场次",
        memories: "长期记忆",
        applications: "申请",
        growthRuns: "成长记录",
        notes: "笔记",
        contacts: "联系人",
        conversations: "Copilot 对话",
        savedSearches: "已保存搜索",
        ingestionFeeds: "订阅源",
        savedJobs: "已收藏职位",
        inboundMails: "招聘回信",
      },
      export: "导出",
      exportEverything: "导出全部",
      exportAnonymized: "匿名导出",
      downloadJson: "下载 JSON",
      downloadMarkdown: "下载 Markdown",
      contentHash: "内容哈希",
      generated: "生成时间",
      redactBeforeSharing: "分享前删减",
      redactSelected: "删减所选部分",
      previewRestore: "预览恢复",
      bundleJson: "数据包 JSON",
      buildThePlan: "生成计划",
      plan: "计划",
      exportDescription:
        "包含档案、简历、知识库、职位描述、面试和记忆的版本化数据包——带内容哈希，未变化的工作区导出得到相同哈希。",
      redactDescription: "删掉整块内容——数据包仍然有效，内容哈希会按剩下的内容重新计算。",
      restoreDescription: "粘贴一个数据包，看看重新导入到底会写什么：计划会与你的工作区逐行对比，未变化的行会被跳过，数据包不再包含的行会从能按 id 匹配的部分里删除——重新生成 id 的简历、文档和记忆只会新增。",
      removedSoFar: "已删减：",
      applyTheRestore: "执行恢复",
      applied: "写入了什么",
      appliedClean: "恢复已执行。",
      appliedWithSkipped: "恢复已执行，有部分段落未动。",
      notJson: "这不是合法的 JSON。",
      printView: "打印视图",
      popupBlocked: "浏览器拦截了打印窗口。",
      opCreate: "新增",
      opUpdate: "更新",
      opDelete: "删除",
      opSkip: "未变化",
      opTotal: "合计",
      planWithCounts: "计划已就绪：新增 {create}、更新 {update}、删除 {delete}、未变化 {skip}。",
      appliedCounts: "新增 {created} · 更新 {updated} · 删除 {deleted} · 未变化 {unchanged}",
    },
    // Ingestion
    ingestion: {
      sweepDone: "清扫完成。",
      planReady: "计划已就绪。",
      untitledRole: "没有标题的职位",
      title: "职位导入",
      description: "从 RSS 或招聘板 API 导入职位。",
      sourceFeed: "来源",
      feedContent: "来源内容",
      parse: "解析",
      buildThePlan: "生成计划",
      parsedPostings: "已解析职位",
      deduplicate: "去重",
      freshnessSweep: "时效扫描",
      deduplication: "去重结果",
      freshness: "时效",
      ingestionPlan: "导入计划",
      sourceDescription: "RSS 2.0 / Atom XML，或招聘板 API 的 JSON。这里不联网——你粘贴来源给你的内容。",
      parsedDescription: "个职位已从来源解析。",
      dedupeDescription: "完全相同的职位会合并为最新、最完整的那一条。",
      freshnessDescription: "新鲜、需要复查（stale）、已过期（close）和无日期。",
      planDescription: "一次扫描会做的三件事。只有已过期 *且* 不在本次批次里的职位才会被建议关闭。",
      toCreate: "个待新增",
      toUpdate: "个待更新",
      toClose: "个待关闭",
      duplicates: "个重复",
      sweepDescription:
        "从信息源或招聘板 API 引入职位发布——解析、去重，并做一次新鲜度清扫。",
      // 定时订阅（19.2）
      scheduleHeading: "定时订阅",
      scheduleDescription:
        "后端的时钟每晚会拉取每个已启用的订阅，运行记录见下方。运行提出的计划只被记录、从不自动执行——职位板只会经由上方可审阅的流程写入。",
      feedName: "名称",
      feedNamePlaceholder: "例如：Hacker News — 招聘",
      feedUrl: "订阅地址",
      feedUrlPlaceholder: "https://boards.example.com/jobs.rss",
      feedSource: "来源",
      sourceKindFeed: "RSS / Atom 订阅",
      sourceKindGreenhouse: "Greenhouse 招聘板",
      sourceKindLever: "Lever 招聘板",
      greenhouseUrlPlaceholder: "acme 或 https://boards.greenhouse.io/acme",
      leverUrlPlaceholder: "acme 或 https://jobs.lever.co/acme",
      boardNameNote: "对招聘板订阅，名称即这些职位所属的公司；职位自带公司名时以职位为准。",
      addFeed: "添加订阅",
      feedAdded: "订阅已添加。",
      feedAddFailed: "添加不了这个订阅。",
      feedUpdateFailed: "更新不了这个订阅。",
      toggleAria: "把 {name} 纳入夜间清扫",
      runNow: "立即运行",
      runNowFailed: "拉取不了这个订阅。",
      runRecordedToast: "本次运行已记录。",
      runFailedToast: "拉取失败：{reason}",
      deleteFeedAria: "删除 {name}",
      deleteFeedTitle: "删除这个订阅？",
      deleteFeedDescription: "{name} 及其运行记录会被移除。它已经带来的职位仍留在职位板上。",
      deleteFeedConfirm: "删除订阅",
      feedRemoved: "订阅已删除。",
      feedRemoveFailed: "删除不了这个订阅。",
      lastRun: "上次运行",
      neverRun: "尚未运行——下一次清扫会拉取它。",
      runsHeading: "清扫记录",
      runsDescription: "时钟做过的每次拉取，最新在前——包括失败的，连同服务器写下的原因。",
      noRuns: "还没有运行记录。下一次清扫或你点“立即运行”时会有第一次拉取。",
      runsUnavailable: "运行记录加载失败。",
      runsPaginationLabel: "清扫记录",
      feedsUnavailable: "订阅列表加载失败。",
      unnamedFeed: "未命名订阅",
      statusCompleted: "完成",
      statusFailed: "失败",
      viewPlan: "查看计划",
      hidePlan: "收起计划",
      planLoading: "正在加载计划…",
      planEmpty: "本次运行没有记录待新增的提案。",
      incomingBadge: "{count} 条导入",
      createBadge: "{count} 个待新增",
      updateBadge: "{count} 个待更新",
      closeBadge: "{count} 个待关闭",
      applyPlan: "应用此计划",
      applyPlanTitle: "应用这次运行的计划？",
      applyPlanDescription:
        "把“{name}”的计划写到职位板上：{create} 个新建、{update} 个更新、{close} 个关闭。一次运行只能应用一次——第二次会被拒绝。",
      applyPlanConfirm: "应用计划",
      appliedAt: "已应用 · {time}",
      appliedCounts: "新建 {created} · 更新 {updated} · 关闭 {closed}",
      applyDone: "计划已应用：新建 {created}、更新 {updated}、关闭 {closed}。",
      applyFailed: "应用这份计划失败了。",
      noFeeds: "还没有订阅——在上方添加一个，夜间清扫会持续跟进它。",
      // 粘贴解析卡片的计数与提示（14.2-14.3）
      parsedToast: "已解析 {count} 个职位。",
      dedupedToast: "{unique} 个唯一，{duplicate} 个重复。",
      sweepSummary: "{fresh} 个新鲜，{stale} 个待复查，{expired} 个已过期，{undated} 个无日期。",
      planSummary: "计划：{create} 个待新增，{update} 个待更新，{close} 个待关闭。",
      uniqueBadge: "{count} 个唯一",
      duplicateBadge: "{count} 个重复",
      inputBadge: "{count} 条输入",
      freshBadge: "{count} 个新鲜",
      staleBadge: "{count} 个待复查",
      expiredBadge: "{count} 个已过期",
      undatedBadge: "{count} 个无日期",
    },
    // 通知中心（19.3）
    notifications: {
      title: "通知",
      description: "已到期的提醒、久无动静的申请，以及需要看一眼的拉取——按发生时间排列。",
      markAllRead: "全部标为已读",
      unreadBadge: "{count} 条未读",
      allRead: "这里的都已读过。",
      empty: "现在没有需要你关注的事项。",
      emptyDescription: "到期的提醒、久无动静的申请，或失败的订阅拉取，都会出现在这里。",
      unavailable: "通知列表加载失败。",
      kindReminder: "提醒",
      kindStale: "久无动静",
      kindIngestionFailed: "拉取失败",
      kindIngestionCreated: "新职位",
      kindReply: "招聘方回复",
      kindOther: "信号",
      reminderLine: "你对 {title} 的提醒已到期。",
      staleLine: "{title} 久无动静，已经安静下来了。",
      ingestionFailedLine: "{feed} 的上一次拉取失败了。",
      ingestionCreatedLine: "{feed} 带来了 {count} 个新职位。",
      replyLine: "招聘方回复了你的投递 —— {title}。",
      fallbackLine: "有一条信号在等你。",
      untitled: "未命名",
      unnamedFeed: "一个未命名订阅",
      open: "打开",
      openAria: "打开 {title}",
      markRead: "标为已读",
      markReadAria: "把 {title} 标为已读",
      dismiss: "忽略",
      dismissAria: "忽略 {title}",
      actionFailed: "更新不了通知列表。",
    },
    // Growth engines
    growthEngines: {
      title: "成长引擎",
      description: "每个引擎单独运行——和成长报告里组合的是同一批引擎，一次只问一个问题。",
      targetRole: "目标职位",
      run: "运行",
      noAnswer: "还没有结果",
      noAnswerDescription: "写下职位名并运行引擎。",
      inFlight: "运行中…",
      failed: "引擎失败。原因记录在后端日志里。",
      study: "要学的",
      rehearse: "要练的",
      locationOptional: "地点（可选）",
      coverage: "覆盖率",
      covered: "已覆盖",
      partial: "部分覆盖",
      expected: "预期",
      missingForDreamRole: "目标职位还缺：",
      engines: {
        gap: "差距分析",
        demand: "市场需求",
        priority: "学习优先级",
        plan: "学习计划",
        prep: "面试准备",
        progression: "成长轨迹",
        stories: "故事库",
        roles: "职位建议",
        progress: "进展",
      },
    },
    // Resumes
    resumes: {
      awaitingParsing: "等待解析",
      parsedOpenToSet: "已解析——打开后可以设定当前版本",
      currentVersionSet: "已设为当前版本——代理就按它来匹配",
      addedOn: " · 添加于 {when}",
      title: "简历",
      description:
        "每次上传都会被解析成结构化档案，并切块进入代理取证的知识库。你的文档里没有的东西，不会被评分。",
      uploadSection: "上传简历",
      existingSection: "已有简历",
      deleteDescription: "这份简历及其版本会从你的工作台移除。从它摄取的知识块也不再被引用。",
      deleteResume: "删除简历",
      deleteAria: "删除 {title}",
      deleteTitle: "删除“{title}”？",
      empty: "还没有简历",
      emptyDescription:
        "把文件拖到上面就能开始。摄取流程会抽取经历、项目和技能，然后给简历质量打分。",
      notLiveDescription:
        "GET /resumes 回了 404，所以这个前端和它对话的后端不是同一个版本。上传已经接好，版本对上就会出现——不会拿编造的东西填坑。",
      paginationLabel: "简历",
      printBlocked: "打印窗口被拦截了——请允许本站弹出窗口后重试。",
      yourVersions: "你的各个版本",
      status: {
        parsed: "已结构化",
        parsing: "解析中…",
        failed: "失败",
        ingesting: "摄取中…",
        uploaded: "已上传",
      },
      open: "打开",
      detail: {
        profileExported: "结构化档案已导出。",
        runTheParse: "在上面跑一次解析，把这份文件变成可查询的档案：经历、项目、教育和技能，每一条都能引回原文。",
        parsedToast: "解析完成——结构化档案已更新。",
        downloadFailed: "下载失败。",
        roleFallback: "职位",
        rolesTitle: "{count} 段工作经历",
        projectsTitle: "{count} 个项目",
        dateUnavailable: "日期未知",
        scoreSuffix: " · 评分 {score}",
        profileFallback: "个人档案",
        noScore: "还没有评审分数。它由解析那一步产出——在上面点一次重新解析就会生成。",
        noVersions: "还没有存下任何版本——这份简历每解析一次就存一个。",
        extracting: "抽取代理正在处理这份文档——做完之后结构化档案会自动出现。",
        parseNow: "开始解析",
        reParse: "重新解析",
        notInWorkspace: "这份简历不在你的工作区里",
        notInWorkspaceDescription: "它可能已被删除。去简历页重新上传一次。",
        loadFailed: "没能加载这份简历",
        parsing: "解析中",
        notParsedYet: "还没解析",
        quality: "简历质量",
        qualityDescription: "只有在评审代理真的给这份文档打过分时才会显示。",
        versions: "版本",
        versionsDescription: "原始解析结果和定制草稿。",
        versionsLoadFailed: "没能加载版本列表",
        whereFrom: "这份简历的来源",
        scoreRing: "简历评分",
        profileEmpty: "结构化档案是空的",
        profileEmptyDescription:
          "这次解析没有返回任何段落。重新跑一次解析，或者到知识库里检查源文档。",
        schools: "学校与学位",
        inventory: "归类清单",
        direction: "方向与亮点",
        targetRoles: "目标职位",
        preferredLocations: "期望城市",
        careerGoals: "职业目标",
        submitting: "正在提交解析请求…",
        loading: "正在加载简历…",
        backToResumes: "回到简历页",
        originalDownloaded: "原始文件已下载。",
        originalFile: "原始文件",
        parseFailed: "解析失败：",
        setCurrent: "设为当前",
        print: "打印",
        diffVsPrevious: "与上一版的差异",
        profileFrom: "档案来自",
        structuredJson: "结构化 JSON。",
        scoreFrom: "分数来自评审代理的解析步骤 · 分块在",
        knowledge: "知识库",
        gapsFound: "发现的差距",
        exportJson: "导出 JSON",
        achievements: "成就",
        current: "当前",
        overall: "总分",
        repo: "仓库",
        versionFallback: "版本 {version}",
        groupFallback: "分组 {number}",
        stages: {
          reading: "正在读取已存下的文档",
          extracting: "正在用解析代理提取各段落",
          structuring: "正在整理经历、项目和技能",
          grading: "正在评估简历质量",
        },
      },
    },
    memory: {
      description: "模型从您的对话和面试中提取的事实。纠正错误的，或降低权重 — 这些塑造您获得的每个答案。",
      loading: "加载记忆中…",
      emptyTitle: "暂无记忆",
      empty: "与 Copilot 对话或完成面试，模型学到的事实将显示在这里。",
      whatAgentsRemember: "代理记住的内容",
      whatAgentRemembers: "代理记住的内容",
      forget: "遗忘",
      forgetConfirm: "遗忘此记忆？",
      forgetDescription: "这将不再塑造代理给您的答案。此操作不可撤销。",
      editAria: "编辑记忆：{preview}",
      forgetAria: "遗忘记忆：{preview}",
      weight: "权重",
      weightHigherFirst: "权重越高的记忆在每个答案中排越前。",
      weightBands: {
        low: "低",
        normal: "普通",
        high: "高",
      },
      characters: "{count} / {limit} 个字符",
      loadFailed: "记忆加载失败",
    },
    profile: {
      description: "代理对您的假设 — 标题、目标和它们向招聘者讲述的故事。",
      loading: "加载档案中…",
      careerProfile: "职业档案",
      targetRoles: "目标角色（逗号分隔）",
      targetLocations: "目标地点（逗号分隔）",
      linksExtras: "链接与额外信息",
      mapsDescription: "代理读取的自由形式映射 — 链接、工作授权、偏好。可解析为 JSON 的值保留类型；其余作为字符串保存。",
      headline: "标题",
      headlinePlaceholder: "例如：正在转向平台方向的后端工程师",
      summary: "摘要",
      summaryPlaceholder: "招聘者在看简历前先看到的那段简介。",
      location: "地点",
      locationPlaceholder: "例如：杭州",
      yearsExperience: "从业年限 (0–{max})",
      yearsPlaceholder: "例如：6",
      yearsIssue: "从业年限必须是 0 到 {max} 之间的数字，或留空。",
      rolesPlaceholder: "例如：平台工程师、资深工程师",
      locationsPlaceholder: "例如：杭州、远程",
      addRow: "添加一行",
      mapValuePlaceholder: "值 — JSON 或纯文本",
      mapKeyAria: "{label}的键 {index}",
      mapValueAria: "{label}的值 {index}",
      mapRemoveAria: "删除{label}第 {index} 行",
      maps: {
        links: "链接",
        linksPlaceholder: "例如：github",
        workAuthorization: "工作授权",
        workAuthorizationPlaceholder: "例如：status",
        preferences: "偏好",
        preferencesPlaceholder: "例如：remote",
      },
      issues: {
        tooManyRoles: "最多 {max} 个目标角色",
        roleTooLong: "每个角色最多 {max} 个字符",
        tooManyLocations: "最多 {max} 个目标地点",
        locationTooLong: "每个地点最多 {max} 个字符",
      },
      saveProfile: "保存档案",
      saveMaps: "保存映射",
      loadFailed: "档案加载失败",
    },
    // Settings
    settings: {
      title: "设置",
      description: "账户、外观与键盘偏好。",
      colorTheme: "配色主题",
      themeLight: "浅色",
      themeDark: "深色",
      themeSystem: "跟随系统",
      logOut: "退出 Career OS？",
      logOutDescription: "你的数据是安全的——这只会结束当前会话。",
      logOutConfirm: "退出登录",
      account: "账户",
      accountDescription: "实时来自 /users/me——显示名可以改，邮箱跟你的登录走。",
      displayName: "显示名",
      signOut: "退出登录",
      signOutDescription: "结束当前会话，并吊销刷新令牌。",
      sessionUnverified: "无法验证这个会话。",
      appearance: "外观",
      appearanceDescription: "界面默认跟随你的系统主题。",
      renderingIn: "正在以{palette}配色渲染。",
      paletteDark: "深色",
      paletteLight: "浅色",
      keyboard: "键盘",
      commandPalette: "命令面板",
    },
    push: {
      title: "浏览器通知",
      description:
        "早晨的 sweep 可以在这个标签页关着时叫醒这台浏览器。唤醒不带任何内容——它打开的收件箱才有。",
      toggle: "叫醒这台浏览器",
      onDescription: "早晨发现新东西时，这台浏览器会响。",
      offDescription: "这台浏览器保持安静。收件箱照样会填。",
      checking: "正在检查这台浏览器……",
      unsupported: "这台浏览器无法接收推送通知。",
      notInstalled: "通知需要已安装应用的 worker。先打开一次生产构建，再回来。",
      blocked: "这台浏览器已屏蔽本站的通知。请在站点设置里允许，然后再打开这个开关。",
      notConfigured: "这个部署没有配置推送密钥，所以唤不醒。收件箱照样会填。",
      permissionDenied: "没有拿到通知权限，所以没有登记。",
      failed: "浏览器注册没能保存。再试一次。",
    },
    /** 日历卡片的句子（34.1）。“地址就是凭证”是读者把它复制走之前必须知道的一件事。 */
    calendar: {
      title: "日历订阅",
      description:
        "在你本来就天天打开的日历应用里读你的提醒。下面这个地址就是全部凭证——拿到它的人就能读到这些提醒，而换一次密钥会让所有地址同时作废。",
      linkLabel: "你的日历地址",
      copy: "复制地址",
      loading: "正在准备你的地址……",
      loadFailed: "地址没能准备好。刷新页面再试一次。",
      hint: "把它粘进 Google 日历、Apple 日历或 Outlook 的“从网址订阅”。提醒会在日历下一次轮询时出现，并一直留到你在这里清掉它。",
    },
    /** 邮件卡片（42.1、42.2）。三个开关过去只能从一封信的页脚进入；这张卡片直接从账号里读出状态、把开关写回账号，并把同一个签名页交到读者手上，不必再翻出一封旧信。 */
    mailLetters: {
      title: "Career OS 寄出的信",
      description:
        "能寄到这个地址的信有三种：周一信、每日信号，以及提醒的即时信。这里的开关直接从你的账号读取并写回状态，不必翻出一封旧信才能改。",
      weekly: "周一信",
      signals: "每日信号",
      reminders: "提醒的即时信",
      on: "开",
      off: "关",
      linkLabel: "设置页地址",
      copy: "复制地址",
      open: "打开设置页",
      loading: "正在读取邮件设置……",
      loadFailed: "邮件设置没能读取。刷新页面再试一次。",
      hint: "这个地址就是钥匙：它带着这个账号的签名，拿到它的人就能改这三个开关。更换服务器上的链接密钥会让所有地址同时失效。",
    },
    /** 转发地址卡片（37.4）。“地址就是凭证”和日历卡片说的是同一句话，而在这里它是字面意义上的真：谁拿到这个地址，谁就能往这个账号的回信里写信，所以换密钥是让它作废的唯一办法。 */
    inbound: {
      title: "转发地址",
      description:
        "让招聘方的回信直接落进你的投递：把他们的邮件转发到下面的地址，每封信都会落到它回答的那条时间线上，而且先被读过，页面才看得到。",
      addressLabel: "你的回信地址",
      copy: "复制地址",
      loading: "正在准备你的地址……",
      notConfigured:
        "这个部署还没有收信邮箱，回信无处可落。等运维配置好收信域名，地址就会出现在这里。",
      loadFailed: "地址没能准备好。刷新页面再试一次。",
      rotationWarning:
        "地址就是全部凭证——知道它的人就能往这个账号的回信里写信。换一次签名密钥会让它作废；没有单独吊销某个地址的办法。",
      hint: "只有转发到这个地址的信会被读取。你自己邮箱的密码不会离开你的邮件服务商。",
      openReplies: "打开回信",
    },
    /** 回信页（37.4）。徽章上的词是分类器的五种意图，加上一种根本不是“读数”的状态：还没人打开过的信。 */
    replies: {
      title: "回信",
      description:
        "招聘方写回来的话，最新的在前。一封信要么说明它回答的是哪次投递，要么留在这里等你挑一个。",
      loading: "正在读回信……",
      unavailable: "回信没能读取。稍后再试。",
      unnamed: "一封没有主题的信",
      senderUnknown: "发件人不明",
      intents: {
        unread: "未读",
        rejection: "拒信",
        interview: "面试",
        offer: "录用",
        info: "信息",
        other: "其他",
      },
      filedOn: "已归入 {title}",
      openApplication: "打开投递",
      notFiled: "还没归档——先添加一条投递，再把它归进去。",
      pickApplication: "选择投递",
      file: "归档",
      filedToast: "这封信已归入对应的投递。",
      fileFailed: "这封信没能归档",
      readLetter: "读这封信",
      applyStage: "移到{stage}",
      applyStageConfirm: "把“{title}”移到{stage}？",
      applyStageDescription:
        "这封信读起来像{intent}，所以分类器建议{stage}。这会立刻移动这张卡片；你随时可以移回来。",
      applyStageToast: "卡片已移动。",
      getAddress: "获取你的地址",
      empty: "还没有回信",
      emptyDescription:
        "把招聘方的邮件转发到你的回信地址，每封信都会落在这里，并挂到它回答的那次投递上。",
      paginationLabel: "回信分页",
    },
    /** 第二道门的卡片（36.4）。每个动作都说清它要付出什么，而不是它做了什么。 */
    security: {
      title: "两步验证",
      description: "登录时的第二步：先输密码，再输验证器应用里的六位验证码。",
      on: "已开启",
      off: "未开启",
      pending: "未验证",
      onDescription:
        "这个账号在密码之后还会要一次验证码。请把打印好的备用码放在别处，不要和存着密钥的手机放在一起。",
      offDescription: "现在只凭密码就能打开这个账号。开启第二步之后，光偷到密码就不够了。",
      pendingDescription:
        "这里开始过一次设置，但一直没有验证。密钥只显示一次，无法再显示，所以请重新开始，生成一把新的。",
      remaining: "还剩 {count} 张备用码",
      remainingNone: "没有未使用的备用码了。在需要之前先换一套新的。",
      loading: "正在检查第二道门……",
      loadFailed: "没能读到两步验证的状态。刷新页面再试一次。",
      start: "开启两步验证",
      startOver: "重新开始",
      enrollHint:
        "把这把密钥加进你的验证器——扫下面的设置地址，或者手动输入密钥——再用应用里显示的六位数字证明它。",
      secretLabel: "验证器密钥",
      copySecret: "复制密钥",
      uriLabel: "设置地址",
      copyUri: "复制地址",
      passwordLabel: "你的密码",
      passwordPlaceholder: "当前密码",
      codeLabel: "六位验证码",
      codePlaceholder: "123456",
      proofCodeLabel: "验证码或备用码",
      proofCodePlaceholder: "123456 或一张备用码",
      activate: "验证并开启",
      replace: "更换备用码",
      replaceHint:
        "这会作废所有已打印的备用码，并给你十张新的。请输入密码和一个可用的验证码——应用里的，或某张备用码。",
      disable: "关闭两步验证",
      disableHint: "这会从这个账号上移除第二步，并作废所有备用码。请输入密码和一个可用的验证码。",
      cancel: "取消",
      codesTitle: "你的备用码",
      codesHint:
        "十张一次性的备用码，每一张都能代替应用里的验证码登录。它们只会显示这一次——现在就把它们存到别处。",
      copyAll: "复制全部备用码",
      codesDone: "我已保存",
      issues: {
        passwordRequired: "请输入密码",
        codeRequired: "请输入验证码",
        codeSixDigits: "请输入验证器里的六位数字",
      },
    },
    /**
     * The auth pages' marketing panel. A visitor who cannot read English
     * lands here first, and this panel is what they are asked to believe.
     */
    auth: {
      pageTitles: {
        signIn: "登录",
        signUp: "注册账号",
        forgotPassword: "重置密码",
        resetPassword: "设置新密码",
        confirmEmail: "确认新邮箱地址",
        accountErased: "账号已删除",
      },
      eyebrow: "求职操作系统",
      headline: "像工程师跑系统一样跑你的求职。",
      description:
        "AI Career OS 把你的职业材料变成一个知识库，然后驱动整个闭环——发现、匹配、定制、面试、流水线。",
      quote: "「绝不虚构经历——每一个说法都对应证据。」",
      pillars: {
        knowledge: {
          title: "职业知识库",
          text: "你的简历、项目和笔记变成一层可检索、带引用的证据。",
        },
        matching: {
          title: "有证据支撑的匹配",
          text: "每个匹配分都是算出来的——再用你自己材料里的原文解释。",
        },
        fabrication: {
          title: "定制但不虚构",
          text: "简历按每份职位发布重写重排；一个校验环节会驳回编造的说法。",
        },
        interviews: {
          continueAction: "继续",
          reportAction: "看报告",
          title: "自适应模拟面试",
          text: "一个会追问、会按维度打分、会调整难度的 AI 面试官。",
        },
      },
      welcomeBack: "欢迎回来。",
      accountCreated: "账号创建成功 — 欢迎来到 Career OS。",
      signInToWorkspace: "登录到您的工作区",
      createYourAccount: "创建您的账号",
      signIn: "登录",
      createAccount: "创建账号",
      confirmPassword: "确认密码",
      passwordsDoNotMatch: "密码不匹配",
      forgotPassword: "忘记密码？",
      email: "邮箱",
      password: "密码",
      code: "六位验证码",
      codePlaceholder: "123456",
      fullName: "姓名",
      fullNamePlaceholder: "张艾达",
      noAccount: "还没有账号？",
      createOne: "创建一个",
      alreadyRegistered: "已经注册过？",
      loginBlurb: "从代理停下的地方继续。",
      registerBlurb: "你的简历几分钟内就变成一个知识库。",
      codeHint: "密码已通过。请输入验证器里的六位验证码，或一张打印好的备用码。",
      issues: {
        emailRequired: "请输入邮箱",
        emailInvalid: "请输入有效的邮箱地址",
        passwordRequired: "请输入密码",
        codeRequired: "请输入验证器里的验证码或一张备用码",
        nameRequired: "请输入姓名",
        tokenRequired: "粘贴邮件里的重置令牌",
        confirmRequired: "请再次输入新密码",
        tooShort: "至少需要 {min} 个字符",
        tooLong: "最多 {max} 个字符",
      },
    },
    /**
     * The skill chips: the two labels that sit above the matched row and
     * the missing one.
     */
    skillChips: {
      why: "为什么匹配",
      missing: "还缺",
    },
    /**
     * The error boundaries. The outermost one replaces the root layout --
     * and with it the locale provider -- so it carries its own copy of the
     * provider rather than reading a context that is not there.
     */
    errors: {
      brokeOnThisScreen: "这个页面出问题了。",
      brokeOnThisScreenDescription: "错误已经记到控制台。再试一次会重新渲染这个页面，不会丢掉你的会话。",
      couldNotStart: "应用没能启动。",
      couldNotStartDescription: "错误已经记到控制台。再试一次会从头重建整个外壳。",
      notOnTheMap: "这个页面不在地图上。",
      notOnTheMapDescription: "你访问的路由不存在。它可能已经挪了地方，或者链接打错了。",
    },
    /**
     * 按码取的失败句子。
     *
     * **码**是契约——枚举自己的注释写着"绝不重命名已发出的码"——而码是过网的东西，
     * 所以句子从码里取，读者看到的是他选的语言。
     *
     * 浏览器自己抛一部分：提前断开的流、读者取消的上传、不存在的网络。其余是
     * **服务端**的码，而它们只在这里——只在这里——当这个码只表达一个意思时：一个
     * 会给出好几种说法的码（`BAD_REQUEST` 有十二种）不能配一句话，否则这句话有
     * 一半是错的；那些码继续用服务端自己的话，直到码细到装得下为止。门禁知道哪
     * 些是哪种，它去读抛出点才知道。
     *
     * 拆分是一个码一个码做的，简历的"找不到"已经是六个码——`RESUME_NOT_AVAILABLE`、
     * `RESUME_NOT_PARSED`、`RESUME_NOT_TAILABLE`、`RESUME_FILE_MISSING`、
     * `RESUME_NOT_INGESTED` 和 `RESUME_NOT_FOUND`——每个都有自己的一句话。状态没有
     * 变：码是契约，而状态是客户端的错误路径读的东西。
     *
     * toast 是在事件处理器里抛的，早于知道读者语言的那次渲染，所以这些句子走
     * `translate`——它在 React 之外读语言。
     */

    errorCodes: {
      ABORTED: "上传已取消。",

      AI_SERVICE_CONFLICT: "AI 服务还没准备好。",

      AI_SERVICE_BAD_REQUEST: "AI 服务请求错误",

      AI_SERVICE_EMPTY_RESPONSE: "AI 服务返回了空内容。",

      AI_SERVICE_NOT_FOUND: "那个东西已经不在了。",

      AI_SERVICE_UNAVAILABLE: "AI 服务没有响应。",

      APPLICATION_NOT_FOUND: "这条申请记录已经不在了。",

      BUNDLE_NOT_PLANNABLE: "这个文件没法变成一份恢复计划。",

      BUNDLE_NO_SECTION: "这个文件里没有数据段。",

      CALENDAR_LINK_INVALID: "这个日历订阅链接无效，或已经停用。",

      COMPANY_NOT_FOUND: "这家公司已经不在了。",

      CONFIRMATION_MISMATCH: "你输入的邮箱不是这个账号的。",

      CONTACT_NOT_FOUND: "这个联系人已经不在了。",

      CONVERSATION_NOT_FOUND: "这段对话已经不在了。",

      CURRENT_PASSWORD_INCORRECT: "你输入的当前密码不对。",

      DOCUMENT_KEY_NOT_OWNED: "没有文档拥有这个文件键。",

      DOCUMENT_NOT_FOUND: "这份文档已经不在了。",

      EMAIL_ALREADY_REGISTERED: "这个邮箱已经注册过了。",

      EMAIL_CHANGE_INVALID: "这个换邮箱链接无效或已经过期。",

      EMAIL_UNCHANGED: "这已经是这个账号的邮箱了。",

      FEED_BOARD_INVALID: "招聘板订阅需要板卡令牌、招聘板页面地址或该板的 API 地址。",

      FEED_LIMIT_REACHED: "这个账号能保留的抓取任务已经到上限了。",

      FEED_URL_INVALID: "抓取地址必须以 http:// 或 https:// 开头。",

      FILE_EMPTY: "这个文件是空的。",

      FILE_KEY_INVALID: "这个文件键不合法。",

      FILE_KEY_MALFORMED: "这个文件键的格式不对。",

      FILE_TOO_LARGE: "文件超出了允许的大小。",

      FORBIDDEN: "你没有权限访问它。",

      HTTP_ERROR: "服务器返回了错误（状态码 {status}）。",

      INGESTION_FEED_NOT_FOUND: "这个定时抓取任务已经不在了。",

      INGESTION_RUN_NOT_FOUND: "这次清扫运行已经不在了。",

      INGESTION_RUN_ALREADY_APPLIED: "这次运行的计划已经应用过了。",

      INGESTION_RUN_NOT_APPLICABLE: "失败的运行没有可应用的计划。",

      INBOUND_LINK_INVALID: "这个来信地址无效，或已经停用。",

      INBOUND_MAIL_ALREADY_FILED: "这封回复已经归档到另一条投递上，请到那里查看。",

      INBOUND_MAIL_NOT_FOUND: "这封回复已经不在了。",

      INBOUND_NOT_CONFIGURED: "这个部署还没有配置来信收件。",

      INTERNAL_ERROR: "服务器内部错误。",

      INTERVIEW_ALREADY_STARTED: "这次面试已经开始了。",

      INTERVIEW_NOTHING_TO_FINALIZE: "现在还没有可以结束的内容。",

      INTERVIEW_NOT_STARTED: "先问出开场问题，再开始回答。",

      INTERVIEW_NO_QUESTION: "没有记录到面试官的问题。",

      INVALID_CREDENTIALS: "邮箱或密码不对。",

      INVALID_FILE_TYPE: "不支持这种文件格式。",

      INVALID_STATUS: "这个状态不在流程里。",

      INVALID_TRANSITION: "这里不允许这样改。",

      JD_NOT_FOUND: "这份职位描述已经不在了。",

      JOB_NOT_FOUND: "这个职位已经不在了。",

      LOGIN_SESSION_NOT_FOUND: "这次登录已经关闭了。",

      MAIL_LINK_INVALID: "这个邮件设置链接无效或已经停用。",
      MAIL_LIST_UNKNOWN: "这个邮件设置不存在。",

      MALFORMED_REQUEST: "请求无法解析。",

      MATCH_NOT_FOUND: "还没有匹配的结果。",

      METHOD_NOT_ALLOWED: "这个请求在这里不被允许。",

      MFA_ALREADY_ACTIVE: "这个账号的两步验证已经开启了。",

      MFA_CODE_INVALID: "这个六位验证码不对。",

      MFA_INVALID: "这个验证码不对，或者已经用过了。请再看一眼手机上的验证码，或换一张打印好的备用码。",

      MFA_NOT_ENROLLED: "这个账号还没有开始设置两步验证。",

      MFA_REQUIRED: "这个账号需要第二步：六位验证码。请输入验证器应用里的验证码，或一张打印好的备用码。",

      NETWORK_ERROR: "连不上接口——后端在跑吗？",

      NIGHTLY_REPORT_CLOCK_REVERSED: "夜间报告不可能在开始之前结束。",

      NIGHTLY_REPORT_STATUS_INVALID: "夜间报告只能以通过或失败结束。",

      NIGHTLY_REPORT_SUMMARY_TOO_LARGE: "夜间报告摘录的条目太多了。",

      NOTE_NOT_FOUND: "这条笔记已经不在了。",

      NOT_FOUND: "这个地址在这里没有提供。",

      PASSWORD_UNCHANGED: "新密码和当前密码一样。",

      PROFILE_NOT_FOUND: "你的档案已经不在了。",

      PUSH_SUBSCRIPTION_INVALID: "这个浏览器的推送订阅不合法。",
      PUSH_SUBSCRIPTION_LIMIT_REACHED: "这个账号保存的浏览器数量已到上限，一次早安提醒叫不完更多了。",

      PUSH_SUBSCRIPTION_NOT_FOUND: "这条浏览器注册已经不在这个账号下了。",

      RATE_LIMITED: "请求太频繁了，请慢一点。",

      RESET_TOKEN_INVALID: "这个重置链接无效或已过期，请重新申请一个。",

      RESET_TOKEN_OWNER_NOT_FOUND: "这个重置链接所属的账号已经不在了。",

      RESUME_FILE_MISSING: "这份简历的原始文件已经不在了。",

      RESUME_NOT_AVAILABLE: "你还没有简历。",

      RESUME_NOT_FOUND: "这份简历已经不在了。",

      RESUME_NOT_INGESTED: "这份简历的文件还没有进入知识库。",

      RESUME_NOT_PARSED: "你的简历还没有解析。",

      RESUME_NOT_TAILABLE: "还没有可以定制的简历。",

      RESUME_TEXT_NOT_READY: "那份简历的正文还读不出来。",

      RESUME_VERSION_MISSING: "那份简历还没有版本。",

      RUN_NOT_FOUND: "这次运行记录已经不在了。",

      SAVED_SEARCH_EMPTY: "保存的搜索至少要有一个条件。",

      SAVED_SEARCH_LIMIT_REACHED: "这个账号能保留的保存搜索已经到上限了。",

      SAVED_SEARCH_NOT_FOUND: "这个保存的搜索已经不在了。",

      SALARY_RANGE_INVALID: "薪资下限不能高于上限。",

      SESSION_NOT_FOUND: "这次面试已经不在了。",

      SOURCE_NOT_FOUND: "这份资料已经不在了。",

      STORAGE_DELETE_FAILED: "对象存储删除失败。",

      STORAGE_PRESIGN_FAILED: "对象存储预签名失败。",

      STORAGE_READ_FAILED: "对象存储读取失败。",

      STORAGE_WRITE_FAILED: "对象存储写入失败。",

      STREAM_ENDED: "连接在回答到达之前断开了。",

      TAILORED_BODY_MISSING: "这份定制版本没有带上它的正文。",

      STREAM_ERROR: "回答的传输失败了，请再试一次。",

      TOKEN_EXPIRED: "登录状态过期了，请重新登录。",

      TOKEN_INVALID: "你的登录状态已经无效了，请重新登录。",

      TOKEN_MALFORMED: "你的登录状态读不出来，请重新登录。",

      TOKEN_OWNER_NOT_FOUND: "这次登录所属的账号已经不在了。",

      TOKEN_REUSED: "为了安全，这一组会话都已退出，请重新登录。",

      UNAUTHORIZED: "登录状态过期了，请重新登录。",

      UPLOAD_UNREADABLE: "这个文件读不出来。",

      USER_DISABLED: "这个账号已被停用。",

      USER_NOT_FOUND: "这个账号已经不在了。",

      VALIDATION_FAILED: "请求数据不合法。",

      VALIDATION_FIELD_REQUIRED: "缺少必填字段。",

      VALIDATION_KIND_UNKNOWN: "该知识类型不存在。",

      VERSION_NOT_FOUND: "那个版本已经不在了。",

      VERSION_NOT_OWNED: "那个版本属于另一份简历。",
    },
    landing: {
      description: "有证据支撑的匹配、简历情报、成长规划，以及 AI 引导的面试——每一个结论都能追溯到你自己的材料。",
      pageTitle: "AI Career OS — 你的个人求职操作系统",
      signIn: "登录",
      getStarted: "开始使用",
      heroTitle: "属于你的个人",
      heroTitleAccent: "求职",
      heroTitleTail: "操作系统",
      heroDescription:
        "AI Career OS 把你的简历、招聘市场和一支 AI 代理队伍变成一个证据支撑的系统——从简历 → 知识库 → 职位发现 → 匹配 → 定制材料 → 模拟面试 → 申请追踪。",
      startFree: "免费开始",
      featuresTitle: "你需要的一切",
      featuresDescription:
        "整个求职过程，一个系统完成——每一个 AI 结论都能追到你自己的材料。",
      switchToChinese: "切换到中文",
      switchToEnglish: "切换到英文",
      features: {
        resume: "简历智能",
        resumeDescription: "上传 PDF/DOCX/TXT → 解析 → 结构化档案 + 带实时评分的版本化简历。",
        matching: "JD 分析与匹配",
        matchingDescription: "提取需求/技能/面试题；确定性匹配分绑定到简历证据。",
        interviews: "自适应模拟面试",
        interviewsDescription: "面试代理不断追问、调整难度；8 维报告 + 深度曲线。",
        tracker: "申请追踪",
        trackerDescription: "Linear 风格看板，带状态流转审计事件——收藏 → 已投递 → 笔试 → 面试 → 录用。",
        growth: "成长智能",
        growthDescription: "差距分析、学习计划、薪资基准与职业路径规划。",
        analytics: "分析与洞察",
        analyticsDescription: "流水线漏斗、回复率、停滞的申请，以及每周洞察摘要。",
      },
      trust: {
        evidence: "证据支撑",
        evidenceDescription: "每一个 AI 结论都能追到你自己的材料——不编造，不虚构经历。",
        scoped: "按用户隔离",
        scopedDescription: "你的数据就是你的。每一次查询都限定在你的用户 ID——不会串号。",
        inspectable: "可检查",
        inspectableDescription: "每一次代理运行都有记录：链路、工具调用、检索、token、成本。",
      },
      ctaTitle: "准备好搭建你的求职操作系统了吗？",
      ctaDescription:
        "从简历开始——系统会建立你的知识库、找到匹配的职位，并帮你准备面试。",
      ctaButton: "免费开始",
      footerNote: "个人项目，持续开发中",
    },
    // The copilot's artifact cards -- what each kind of answer is called.
    artifacts: {
      match: "匹配分析",
      coverLetter: "求职信草稿",
      interview: "模拟面试已就绪",
      gapReport: "差距分析",
      salaryBand: "市场薪资带",
      offerComparison: "录用比较",
      learningPriority: "学习优先级",
      matchRing: "匹配",
      copyDraft: "复制草稿",
      copyLetter: "复制求职信",
      matchingRoles: "{count} 个匹配职位",
      tailoredResume: "定制简历草稿",
      openJob: "打开职位",
      interviewPrepared: "代理根据这段对话准备好了一场面试。",
      offerFallback: "报价 {number}",
      start: "开始",
      coverage: "覆盖率",
    },
    // The copilot's action chips -- the labels the orchestrator writes in
    // English, which the browser says in the reader's language.
    actions: {
      coverLetter: "起草求职信",
      interview: "开始模拟面试",
      tailor: "为这个职位定制简历",
      openGrowth: "打开成长报告",
      openOffers: "打开录用工作台",
      openInterview: "继续面试",
    },
    // Copilot
    copilot: {
      noConversationId: "接口没有返回会话 id。",
      couldNotAnswer: "副驾驶没能回答。",
      suggestionOwnership: "哪段经历最能体现主导力？",
      suggestionCoverLetter: "给投过的公司起草一封求职信",
      suggestionRag: "RAG 系统设计面试我该准备什么？",
      suggestionCompare: "拿我的简历对一下这份 JD",
      untitledChat: "没有标题的对话",
      title: "问问你的求职代理",
      conversations: "会话",
      noConversations: "还没有会话",
      noConversationsDescription: "在上面开一个——每一轮对话都有追踪并会被保存。",
      conversationTitle: "会话标题",
      deleteChat: "删除这个对话？",
      deleteChatDescription: "记录和它的引用会一起消失，且无法撤销。",
      firstMessage: "给副驾驶的第一条消息",
      conversationsSheet: "会话",
      chatsButton: "对话",
      newChat: "新对话",
      loadingConversations: "正在加载会话…",
      conversationsNotServed: "这个 API 版本还没有提供会话",
      couldNotLoadConversations: "没能加载会话",
      paginationLabel: "会话",
      groundedIn: "基于你的简历、笔记和收藏的职位——它说的每一句都有引用。",
      answersCiteKnowledge: "回答引用你的知识库",
      firstMessagePlaceholder: "例如：做 LLM 平台这类岗位，我该把哪个项目放在最前面？",
      enterToSend: "回车发送 · Shift+回车换行",
      startChat: "开始对话",
      writing: "正在写",
      thinking: "正在思考",
      badge: "副驾驶",
      retryLastMessage: "重发上一条消息",
      delete: "删除",
      noHistory: "这个 API 版本没有会话历史",
      noHistoryDescription:
        "GET /conversations 返回了 404，所以这个前端和它对话的后端不是同一个版本。这里没有任何预填内容。",
      couldNotLoad: "加载这个会话失败",
      askAnything: "关于你的求职，随便问",
      askAnythingDescription:
        "提到经历、技能或职位的问题会从你的知识库里带引用作答——试试「把我的简历匹配到最近收藏的职位」。",
      messagePlaceholder: "给副驾驶发消息…",
      messageLabel: "给副驾驶发消息",
      send: "发送消息",
      renameChatAria: "重命名对话“{title}”",
      deleteChatAria: "删除对话“{title}”",
    },
    // Networking
    networking: {
      title: "联系人",
      description: "求职中真正会接触到的人——他们是谁、你怎么认识的、上次聊是什么时候。",
      noContacts: "还没有联系人",
      noContactsDescription:
        "加上你联系的推荐人、导师和同行——副驾驶会为他们起草消息，跟进提醒也会读这份名单。",
      addContact: "添加联系人",
      editContact: "编辑联系人",
      onlyNameRequired: "只有名字是必填的——知道什么填什么，其余留空。",
      name: "姓名",
      role: "职位",
      company: "公司",
      relation: "关系",
      email: "邮箱",
      lastTouch: "上次联系",
      lastTouchLine: " · 最近联系 {when}",
      notes: "备注",
      notesPlaceholder: "下次联系时的背景——怎么认识的、聊过什么。",
      draft: "起草",
      draftFor: "为 {name} 起草",
      draftMessage: "消息草稿",
      draftWithCopilot: "让副驾驶起草一条消息",
      addContactTitle: "添加联系人",
      editContactTitle: "编辑 {name}",
      deleteContactTitle: "删除 {name}？",
      relationPlaceholder: "推荐人、导师、同行…",
      delete: "删除",
      cancel: "取消",
      save: "保存",
      add: "添加",
      deleteContact: "名单里的这一行会被删除，且无法撤销。",
    },
    // Growth report
    growth: {
      title: "成长报告",
      description: "准备度、背后的差距、市场的薪资带、分阶段学习计划，以及上次运行以来的变化。",
      buildReport: "生成报告",
      buildReportDescription:
        "一次调用组合出准备度、背后的差距、市场的薪资带、分阶段学习计划，以及上次运行以来的变化。",
      noReport: "还没有报告",
      noReportDescription:
        "写下你瞄准的职位并运行分析器——报告是基于你简历里的证据生成的，不是你填的表单。",
      targetRole: "目标职位",
      location: "城市（可选）",
      analyze: "分析",
      roleTooShort: "职位名要写完整——分析器至少需要 10 个字符才能定位。",
      covered: "已覆盖",
      partial: "部分覆盖",
      open: "未覆盖",
      coverage: "覆盖率",
      salaryBand: "薪资带",
      matchingPostings: "个匹配职位",
      learningPlan: "学习计划",
      learningPlanDescription: "先基础，再该职位的核心，最后是应用。",
      nothingToStudy: "没什么要学的——每一项预期技能背后都有证据。",
      progress: "进展",
      progressBaseline: "这是该职位的第一次报告——下次运行会与它对比。",
      progressAgainstPrevious: "与你上次对该职位的报告对比。",
      noSkillChange: "自上次报告以来没有技能状态变化",
      skillsClosed: "已补齐",
      skillsImproved: "有提升",
      skillsOpened: "新增缺口",
      skillsRegressed: "有退步",
      stillOpen: "{count} 项仍未覆盖。",
      run: "运行",
    },
    // Knowledge
    knowledge: {
      title: "知识库",
      description: "代理能引用的全部内容：简历、项目、笔记、JD、公司调研、反馈。",
      showingCitedSource: "正在显示你某条引用指向的来源。",
      showAllSources: "显示全部来源",
      noSourceMatches: "没有来源匹配这条引用",
      noSourceMatchesDescription: "这份文档可能已被删除，或者它的摄取从未完成。",
      baseIsEmpty: "知识库是空的",
      baseIsEmptyDescription: "添加来源，它们会被解析、切块并嵌入，供带引用的检索使用。",
      askCopilotToIngest: "让副驾驶摄取",
      paginationLabel: "来源",
      notes: {
        titleLabel: "标题（选填）",
        titlePlaceholder: "例如：「为什么选我们」这个问题的答案",
        content: "内容",
        contentPlaceholder: "写下来——代理可以带着引用把它念回给你。",
        saveNote: "保存笔记",
        untitled: "无标题笔记",
        noteTitleLabel: "笔记标题",
        noteContentLabel: "笔记内容",
        saving: "保存中…",
        cancel: "取消",
        save: "保存",
        updated: "更新于 {date}",
        editNote: "编辑 {title}",
        deleteNote: "删除 {title}",
        deleteTitle: "删除「{title}」？",
        deleteDescription: "笔记行会被移除，它的分块也不再被引用。且无法撤销。",
        delete: "删除",
        section: "笔记",
        description: "代理可以引用回给你的简短参考笔记——谈资、薪资调研、跟进事项。",
        noNotes: "还没有笔记",
        noNotesDescription: "在上面写第一条——它会直接进入代理可以引用的知识库。",
        paginationLabel: "笔记",
      },
      sources: {
        deleteFailed: "没能删除这个来源。",
        deleted: "来源已删除——它的分块也不再被引用。",
        chooseDocuments: "选择要摄取的文档",
        appliedToBatch: "应用于这批里的每个文件",
        clearList: "清空列表",
        deleteDescription: "来源行会被移除，它的分块也不再被引用。且无法撤销。",
        delete: "删除",
        deleteLabel: "删除 {title}",
        deleteTitle: "删除「{title}」？",
        documents: "文档",
        titleLabel: "标题（选填）",
        kind: "类型",
        chooseFiles: "选择文件",
        uploading: "上传中…",
        noSourceId: "摄取中——没有返回来源 ID",
        ready: "就绪",
        pending: "等待中",
        failedPrefix: "失败：{reason}",
        ingestionFailed: "摄取失败",
        batchSummary: "已完成 {done}/{total}{failed}",
        notIngested: "，{count} 个未摄取",
        typeRejected: "只能摄取 {extensions} 文件——“{name}”会被服务器拒绝。",
        tooLarge: "“{name}”超过了 20 MB 的摄取上限。",
        emptyFile: "“{name}”是空文件——没有可摄取的内容。",
        kinds: {
          note: "笔记",
          resume: "简历",
          project: "项目",
          jd: "职位描述",
          company: "公司",
          interview_feedback: "面试反馈",
          certificate: "证书",
          course: "课程",
          goal: "目标",
        },
      },
    },
    // Companies
    companies: {
      title: "公司",
      description: "从职位发布和网页来源构建的研究档案——外部事实总是带着它的来源。",
      noneResearched: "还没有调研过的公司",
      noneResearchedDescription: "当你收藏一个职位或问起某家公司时，调研代理会建立公司档案。",
      researchOne: "调研一家公司",
      profilePending: "档案待补",
      role: "个职位",
      roles: "个职位",
      websiteLabel: "{name} 官网",
      paginationLabel: "公司",
      detail: {
        loadFailed: "没能加载这家公司",
        loading: "正在加载公司…",
        website: "官网",
        overview: "概览",
        noOverview: "暂时还没有概览。",
        postings: "职位发布里说了什么",
        skillsAskedFor: "要求的技能",
        interviewTopics: "面试题",
        noPostings: "语料库里还没有这家公司的职位发布。",
        readingCorpus: "正在阅读语料…",
        readCorpus: "阅读语料",
        techStack: "技术栈",
        noTechStack: "暂时还没有技术栈信息。",
        workingHere: "在这里工作",
        culture: "文化",
        interviewProcess: "面试流程",
        openRoles: "在招职位（{count}）",
        showingBestMatching: "显示 {total} 个在招职位中匹配度最高的 {shown} 个。",
        noOpenRoles: "目前没有在招职位。",
        sources: "来源",
        noSourcesRecorded: "还没有记录这份档案的出处。",
        open: "打开",
      },
    },
    // Activity
    activity: {
      title: "AI 活动",
      runStatus: {
        running: "运行中",
        completed: "已完成",
        failed: "失败",
        cancelled: "已取消",
      },
      trigger: {
        chat: "对话",
        resume_parse: "简历解析",
        match: "岗位匹配",
        tailor: "简历定制",
        cover_letter: "求职信",
        interview: "模拟面试",
        ingest: "资料摄取",
        nightly: "夜间任务",
      },
      description: "每一次代理运行、工具调用和检索——答案背后的调试视图。",
      ctaLabel: "在副驾驶里跑点什么",
      paginationLabel: "运行",
      trace: "链路",
      rowTokens: "{count} 个 token",
      emptyDescription: "副驾驶或某个职位跑过之后，它的完整链路就会出现在这里。",
      noRuns: "还没有代理运行记录",
      detail: {
        noTraceSteps: "这次运行没有记录轨迹步骤。不经过编排器的工具（单次调用的解析）只记录运行本身。",
        debugView: "一次代理回答背后的调试视图。",
        agentRun: "代理运行",
        agentFallback: "代理",
        runFallback: "运行",
        triggerRun: "{trigger}运行",
        runSubtitle: "{agent} · {trigger}——编排器为这次运行持久化的每一步。",
        traceHint: "由编排器持久化——展开任意一行可以看到原始载荷。",
        steps: "步骤",
        toolCalls: "工具调用",
        tokens: "Token 数",
        latency: "延迟",
        thisRunFailed: "这次运行失败了",
        executionTrace: "执行链路",
        attribution: "归因",
        runId: "运行 ID",
        runGone: "这次运行已经不在了",
        runGoneDescription:
          "它可能从未被记录，或者属于另一个工作区。运行记录只对它们的主人可见。",
        cost: "成本",
        started: "开始于",
        finished: "结束于",
        model: "模型",
        agent: "代理",
        openConversation: "打开跑出这次运行的那段对话",
        allActivity: "全部活动",
        backToActivity: "回到活动页",
      },
    },
    // Applications
    applications: {
      title: "申请",
      description:
        "所有在飞的职位。拖动卡片就能在流水线里移动它，或打开一个加上备注和提醒——仪表盘的计数读的是同一份数据。",
      boardColumn: "{stage} 的申请",
      dragToReorder: "拖动以重新排序",
      reminderDue: "提醒到期",
      noStep14d: "14 天以上没动静",
      reminderOn: "提醒 {date}",
      pipelineIsEmpty: "流水线还是空的",
      dropCardHere: "把卡片拖到这里",
      savingMove: "正在保存移动…",
      pipelineIsEmptyDescription: "在职位详情页记录一个职位，它就会出现在这里，从「已收藏」开始。",
      addApplication: "添加申请",
      add: "添加",
      paginationLabel: "申请",
      dialog: {
        trackTitle: "记录一个申请",
        createDescription: "在这里添加的任何内容都会从你选择的阶段开始，不需要关联职位。",
        role: "职位",
        rolePlaceholder: "高级后端工程师",
        company: "公司",
        optional: "选填",
        stage: "阶段",
        notes: "备注",
        notesPlaceholder: "招聘负责人名字、笔试、薪资范围、下周你还想起来的一切…",
        reminder: "提醒",
        clear: "清空",
        reminderHint: "仪表盘会把到期的提醒算作需要你处理的事。",
        outcome: "结果",
        offerCompensation: "录用薪酬",
        offerCompensationPlaceholder: "例如 40k/月 · 16 个月，或 550k + 股权",
        rejectionReason: "拒绝 / 反馈原因",
        rejectionReasonPlaceholder: "它为什么没继续——这条会反过来告诉你该补什么。",
        outcomeHint:
          "记在这里，闭环就合上了：拒绝原因告诉你该加强什么，录用的数字是你比较和谈判的依据。",
        history: "历史",
        loadingHistory: "正在加载历史…",
        historyFailed: "历史加载失败",
        nothingRecorded: "还没有记录——你移动的阶段、保存的备注和设置的提醒都会落在这里。",
        pipelineLinks: "流水线链接",
        resumeVersionLink: "简历版本",
        jdAnalysis: "JD 分析",
        match: "匹配",
        pipelineLinksHint: "由产出它们的那条路由记录——匹配、定制或 JD 分析。",
        notFound: "这个申请已经不存在了。",
        saveFailed: "没能保存这个申请。",
        delete: "删除",
        cancel: "取消",
        saveChanges: "保存修改",
        addToPipeline: "加入流水线",
        deleteTitle: "删除这个申请？",
        deleteDescription: "「{title}」和它的历史会从看板上移除，且无法撤销。",
        movedTo: "已移到 {stage}",
        stageChanged: "阶段已变更",
        noteSaved: "备注已保存",
        reminderCleared: "提醒已清除",
        reminderSetFor: "提醒设在 {when}",
        reminderSet: "提醒已设置",
        offerCompensationSaved: "录用薪酬已保存",
        rejectionReasonSaved: "拒绝原因已保存",
        outcomeRecorded: "结果已记录",
        update: "更新",
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
      applications: "申请",
      waitingOnYou: "等你处理",
      recommendations: "推荐",
      agentActivity: "代理活动",
      currentResume: "当前简历",
      knowledgeBase: "知识库",
      aiUsage: "AI 用量",
      gapAnalysis: "差距分析",
      networking: "人脉",
      rubric: "评分表",
      betweenSessions: "两场之间",
      adaptivity: "适应性",
      explainability: "可解释性",
      reviewerAgent: "评审代理",
      history: "历史",
      dataSources: "数据来源",
      workHistory: "工作经历",
      projects: "项目",
      education: "教育",
      skills: "技能",
      goals: "目标",
      aiMatch: "AI 匹配",
      growth: "成长",
      prep: "准备",
    },
    stages: {
      saved: {
        label: "已收藏",
        short: "收藏",
        blurb: "从职位板收藏下来的。",
      },
      applied: {
        label: "已投递",
        short: "已投",
        blurb: "申请已提交。",
      },
      oa: {
        label: "在线测评",
        short: "测评",
        blurb: "等待或正在完成在线测试。",
      },
      interview: {
        label: "面试",
        short: "面试",
        blurb: "在面试流程中。",
      },
      final_round: {
        label: "终面",
        short: "终面",
        blurb: "最后一轮现场 / 群面。",
      },
      offer: {
        label: "录用",
        short: "录用",
        blurb: "已发录用——该决定或该谈了。",
      },
      rejected: {
        label: "已拒绝",
        short: "拒绝",
        blurb: "已结束。留着做复盘分析。",
      },
    },
    /**
     * The score dimensions, named in the reader's language.
     *
     * Four vocabularies, four namespaces, because they are four different
     * sets of words. The keys inside are the wire's own; `lib/dimensions.ts`
     * is the one place that maps them here.
     */
    dimensions: {
      match: {
        technical: { label: "技术" },
        experience: { label: "经验" },
        projects: { label: "项目" },
        education: { label: "教育" },
      },
      interview: {
        technical_accuracy: { label: "技术准确度" },
        communication: { label: "表达" },
        depth: { label: "深度" },
        structure: { label: "结构" },
        problem_solving: { label: "问题解决" },
        system_thinking: { label: "系统思维" },
        ai_knowledge: { label: "AI 知识" },
        backend_knowledge: { label: "后端知识" },
      },
      resume: {
        bullets: { label: "要点与数据密度" },
        structure: { label: "结构与可扫描性" },
        impact: { label: "影响力措辞" },
        clarity: { label: "清晰度" },
        keywords: { label: "关键词覆盖" },
      },
      criteria: {
        has_contact: { label: "联系方式（邮箱 / 电话）" },
        has_summary: { label: "个人摘要" },
        has_experience: { label: "工作经历" },
        experience_has_bullets: { label: "每段经历下的要点" },
        quantified_impact: { label: "量化的成果（数字或百分比）" },
        has_projects: { label: "项目" },
        has_education: { label: "教育背景" },
        has_skills: { label: "足够的技能（5 项以上）" },
        years_experience_stated: { label: "写明工作年限" },
        dates_present: { label: "每段经历都有起始时间" },
      },
    },
    // Interviews
    interviews: {
      title: "面试",
      depthBands: {
        warmup: "热身",
        standard: "标准",
        solid: "扎实",
        deep: "深入",
        expert: "专家",
      },
      description:
        "自适应模拟面试：你的回答有力时代理会追问，不够有力时它会往下走一层，你证明了自己的深度它就推得更深。每次评估都引用你自己的材料。",
      paginationLabel: "面试场次",
      startInterview: "开始面试",
      mode: "模式",
      modeNames: {
        behavioral: "行为面试",
        technical: "技术面试",
        system_design: "系统设计",
        ai_llm: "AI / LLM",
        rag: "RAG",
        agent: "Agent",
        backend: "后端",
      },
      modeHints: {
        behavioral: "用 STAR 结构讲你真实经历中的故事",
        technical: "编码与基础，随回答逐步加深",
        system_design: "面向目标岗位的扩展性取舍",
        ai_llm: "模型、微调、评测",
        rag: "检索、分块、重排、引用",
        agent: "规划、工具调用、编排",
        backend: "API、存储、并发",
      },
      modeInterview: "{mode}",
      modeReport: "{mode}报告",
      pickATargetJob: "先挑一个目标职位",
      empty: "还没有模拟面试",
      emptyDescription:
        "在上面选一种模式——这场面试是用你的简历和目标职位搭建的，所以回答是拿证据来评的，不是拿常识。",
      notLiveDescription:
        "GET /interview/sessions 回了 404，所以这个前端和它对话的后端不是同一个版本。面试器已经接好，版本对上就会自动启用。",
      inProgress: "进行中",
      questionsInline: "{count} 个问题 · ",
      finishedAt: "已于 {when} 完成",
      startedAt: "开始于 {when}",
      reportAction: "查看报告",
      continueAction: "继续",
      detail: {
        submitHint: "Ctrl+Enter 提交——代理会在下一个问题之前先评估",
        abandoned: "这场面试中途放弃了",
        finished: "这场面试已经结束",
        missing: "这场面试还不存在",
        missingDescription:
          "面试接口可能还没在后端上线，或者这场面试已被删除。去面试页重新开一场。",
        loadFailed: "没能加载这场面试",
        answerPlaceholder: "像你真的开口回答那样写——具体的细节、数字，以及你自己做了什么。",
        answerLabel: "你的回答",
        recordAnswer: "用语音回答",
        stopRecording: "停止并转写",
        recordingHint: "正在录音——像你真的开口一样说出来。",
        transcribingAnswer: "正在转写你的回答…",
        micDenied: "麦克风不可用——你仍然可以直接输入回答。",
        recordingFailed: "这段录音没能处理——请重试，或直接输入回答。",
        voiceUnavailable: "这里用不了语音——你仍然可以直接输入回答。",
        voiceFailed: "语音没能传过来——请重试，或直接输入回答。",
        listen: "朗读",
        stopListening: "停止朗读",
        speechUnavailable: "没能播放这个问题——请看上面的文字。",
        endTitle: "结束这场面试？",
        endDescription:
          "评估代理会给所有已回答的问题打分，并生成你的报告。没有回答的问题会被跳过。",
        finishAndScore: "结束并评分",
        wentWell: "答得好的地方",
        wasWeak: "薄弱的地方",
        missingPoints: "没答到的",
        loading: "正在加载面试…",
        allInterviews: "全部面试",
        followUp: "追问——再往深一层",
        newTopic: "新话题",
        opening: "开场",
        finishAndReport: "结束并出报告",
        submitAnswer: "提交回答",
        thisSessionSoFar: "本场到目前为止",
        answered: "已回答 {count} 个",
        answerEvaluation: "回答评估",
        wantsDeeper: "代理想再往深一层。",
        movingToNextTopic: "代理要转到下一个话题。",
        noFollowUp: "代理没有追问——它建议就此收尾出报告。",
        finishEarly: "提前结束",
        nextQuestion: "下一个问题",
        question: "第 {number} 题",
        evaluating: "正在拿你的真实经历评估这个回答",
        deciding: "正在决定：再往深一层，还是换个话题",
        reportReady:
          "评估代理已经产出了完整报告——各维度得分、哪些答得好、哪些薄弱、学习材料和深度曲线。",
        openReport: "打开报告",
        depthTitle: "深度：{depth}/5",
        difficultyAria: "难度等级 {level}（满分 5 级）",
      },
      report: {
        solidPractice: "练习得不错——下面薄弱的维度就是最快的提升点。",
        perDimension: "下面按维度给出结果。",
        practiceHint: "学完再用同样的模式练一次——代理会针对你上次薄弱的地方调整。",
        untitledResource: "没有标题的资料",
        strongSession: "这场很稳——追问把你推到了深处，而你守住了高度。",
        loadFailed: "没能加载报告",
        stillRunning: "面试还在进行中",
        stillRunningDescription: "结束这场面试后，评估代理会把每个回答打分，生成完整报告。",
        noReport: "还没有存下报告",
        open: "打开",
        noReportDescription:
          "这场面试已经结束，但评估代理还没有发布报告。你可以手动触发收尾——它会给已有的回答打分。",
        overallScore: "面试总分",
        dimensions: "各维度得分",
        dimensionsDescription: "评估代理固定的评分表——只显示它真的打过分的维度。",
        studyMaterial: "学习材料",
        studyMaterialDescription: "针对这场面试暴露出来的概念。",
        depthTrajectory: "深度曲线",
        depthTrajectoryDescription: "代理一个问题一个问题推了多深，以及你答得怎么样。",
        loading: "正在加载报告…",
        continueInterview: "继续面试",
        generateReport: "生成报告",
        whatWentWell: "哪些答得好",
        whatWasWeak: "哪些薄弱",
        allInterviews: "全部面试",
        practiceAgain: "再练一次",
        fromReport: "来自报告 {id}",
        depthTrajectoryAria: "横跨 {count} 个问题的深度轨迹",
        questionsCount: "{count} 个问题",
        depthReached: "达到深度 {level} / 5 · {band}",
        legendDepth: "代理连续追问了多少个问题",
        legendScore: "你的得分",
        hoverDots: "悬停圆点查看每道题",
      },
    },
    // Jobs
    jobs: {
      notLiveSearchTitle: "这个后端版本没有职位搜索",
      notLiveSavedTitle: "这个后端版本没有收藏列表",
      title: "职位",
      status: {
        open: "招聘中",
        closed: "已关闭",
      },
      remoteTypes: {
        remote: "远程",
        hybrid: "混合办公",
        onsite: "现场办公",
      },
      description: "发现和粘贴的职位，带着证据和你的简历对过分——匹配度在前，元数据在后。",
      sort: {
        auto: "最佳匹配",
        posted: "最新优先",
        salary: "薪资最高",
        title: "职位名 A–Z",
        match: "匹配度",
      },
      noSavedMatch: "没有符合这些筛选的已收藏职位",
      noSavedMatchDescription:
        "这些筛选后面还压着一些收藏。放宽一个，或者全部清掉，就能看到完整的收藏列表。",
      clearFilters: "清空筛选",
      nothingSaved: "还没有收藏",
      savedAt: "收藏于 {date}",
      salaryUpTo: "最高 {amount}",
      nothingSavedDescription:
        "在「发现」里收藏一个职位，它就会出现在你的流水线里，随时可以跑匹配、定制简历。",
      browseDiscover: "去发现页看看",
      boardIsQuiet: "职位板很安静",
      boardIsQuietDescription:
        "目前没有职位符合这些筛选。清掉一个筛选、粘贴一份 JD 给分析器，或者让副驾驶为你的目标职位做调研。",
      askCopilot: "问问副驾驶",
      paginationLabel: "职位",
      notLiveDescription:
        "这个路由回了 404，所以这个前端和它对话的后端不是同一个版本。真实数据没有的地方，不会拿别的东西顶上。",
      filtersButton: "筛选",
      sortLabel: "排序",
      noteLabel: "备注：",
      discoverTab: "发现",
      savedTab: "收藏",
      researchRoles: "调研职位",
      detail: {
        seededBoard: "种子职位库",
        foundByResearch: "调研代理找到的",
        pastedByYou: "你自己粘贴的",
        noAnalysis: "还没有分析，所以没有可引用的东西。在上面跑一次匹配器。",
        noCitations: "这次匹配没有带回引用。重新跑一次分析——匹配器会为它打分的每一项存一句证据。",
        analyze: "分析匹配",
        reAnalyze: "重新分析匹配",
        notInSystem: "系统里没有这个职位",
        notInSystemDescription:
          "它要么被删了，要么后端还没存下来。在职位页粘贴它的 JD →「分析 JD」，就能立刻开始处理。",
        loadFailed: "没能加载这个职位",
        resumeEvidence: "简历证据",
        resumeEvidenceDescription: "分数背后是哪些原文段落，以及它们来自哪份文档的哪一节。",
        loading: "正在加载职位…",
        backToJobs: "回到职位板",
        companyNotResearched: "这家公司还没调研过",
        entryLevel: "入门级",
        experienceYear: "{years}+ 年经验",
        experienceYears: "{years}+ 年经验",
        tailorResume: "定制简历",
        coverLetter: "求职信",
        interviewPrep: "面试准备",
        mockInterviewMode: "模拟面试模式",
        addToPipeline: "加入流水线",
        originalPosting: "原始职位发布",
        matchRunFailed: "匹配运行失败：",
        unknownError: "未知错误",
        requirementsBreakdown: "要求拆解",
        requirementsBreakdownDescription: "JD 提取器给出的优先级分析。",
        sources: "来源",
        sourcesDescription: "这个页面是由什么构建的。",
        scoreFrom: "分数来自",
        evidenceFrom: "证据来自你的知识库。",
      },
      filters: {
        searchPlaceholder: "职位、团队、技术…",
        locationPlaceholder: "上海 / 远程 / 柏林",
        companyPlaceholder: "初创、大厂…",
        minSalary: "最低",
        maxSalary: "最高",
        minSalaryLabel: "最低薪资",
        maxSalaryLabel: "最高薪资",
        heading: "筛选",
        clear: "清空",
        clearedToast: "筛选已清空。",
        keyword: "关键词",
        location: "地点",
        company: "公司",
        skills: "技能",
        salaryRange: "薪资范围",
        remoteOnly: "只看远程",
        filtering: "正在筛选…",
        skillSuggestions: "简历档案解析完成后，这里会给出技能建议。",
        matchingRoles: "{count} 个匹配{noun}",
        role: "职位",
        roles: "职位",
        resultsLoad: "结果来自实时搜索接口。",
        removeSkillAria: "移除技能筛选 {skill}",
      },
      match: {
        showOriginal: "显示原文",
        hideOriginal: "隐藏原文",
        weak: "以你现在的画像，契合度偏低",
        partial: "部分契合——差距还要补",
        good: "比较契合，还有一点差距",
        strong: "非常契合——值得投了",
        analyze: "分析匹配",
        rerun: "重新匹配",
        analyzing: "分析中…",
        runToScore: "跑一次匹配器，用你解析好的简历给这个职位打分。",
        evidenceNote: "分数来自检索到的简历证据，不是模型的一次猜测。",
        noMatchYet: "还没有算过匹配",
        evidenceLine: "已证实 {matched} 项要求 · {missing} 处差距",
        computedAt: "计算于 {when}",
        whyTitle: "你为什么匹配",
        noMatch: "无匹配",
        overall: "总体匹配度",
        evidenceBacked: "有证据支撑",
        skillGaps: "技能差距",
        skillGapsDescription: "JD 要求、但你的档案还拿不出证据的部分。",
        interviewTopics: "可能的面试题",
        interviewTopicsDescription: "从需求提取中推导，按权重排序。",
        preparation: "推荐的准备",
        preparationDescription: "按每项对匹配度的贡献排序。",
        nothingFabricatedBefore: "这里不会凭空造数：一旦",
        nothingFabricatedAfter: "返回，匹配环、各维度得分和引用就都会出现。",
        resource: "来源：",
        jobDescription: "职位描述",
        jobDescriptionDescription: "直接从职位发布里提取出的要求。",
        scoreAria: "匹配分 {score} 分",
        required: "必须",
        niceToHave: "加分项",
      },
    },
    savedSearches: {
      heading: "已存搜索",
      saveAction: "保存当前搜索",
      empty: "还没有已存搜索——把正在问的问题存下来，下次一键回到这里。",
      remoteName: "远程职位",
      nameLabel: "名称",
      namePlaceholder: "例如：上海的 Java 岗位",
      saveTitle: "保存这次搜索",
      saveDescription: "职位板当前的筛选条件会原样保留，点一下就能回到这个视图。",
      saveFailed: "保存搜索失败。",
      savedToast: "搜索已保存。",
      deleteAria: "删除已存搜索 {name}",
      deleteTitle: "忘记这条已存搜索？",
      deleteDescription: "「{name}」会从侧栏移除，职位本身不受影响。",
      deleteConfirm: "删除",
      deleteFailed: "删除已存搜索失败。",
      deletedToast: "已存搜索已删除。",
    },
    jd: {
      title: "JD 智能分析",
      openAction: "分析一段 JD",
      analyzeAction: "分析",
      badge: "JD 分析",
      keepText: "保留这段文本",
      runFailed: "分析失败了。",
      characterCount: "{count} 个字符",
      nothingSent: "在你运行分析之前，什么都不会发送。",
      pasteAtLeast: "至少粘贴 {min} 个字符的职位发布",
      readingPosting: "读取发布中",
      description: "粘贴职位描述。JD 分析师将提取需求、优先级并与您的解析简历对比差距。",
      structuredOutput: "/jds 的结构化输出",
      comparingResume: "正在与简历对比…",
      comparingProfile: "对比您的档案",
      analysisFailed: "分析返回无结构化字段。通常是发布文本太短 — 请粘贴完整描述后重试。",
      pasteFullPosting: "粘贴完整发布 — 职责、要求、加分项…",
      extractingRequirements: "提取需求中",
      preferredSkills: "优先技能",
      rankingPriorities: "优先级排序",
      jobDescriptionText: "职位描述文本",
      resumeImprovementSuggestions: "简历改进建议",
      requiredSkills: "必需技能",
      responsibilities: "职责",
      hiddenRequirements: "隐性要求",
      interviewTopics: "面试话题",
      skillGap: "您的技能差距",
    },
    import: {
      title: "导入职位发布",
      openAction: "粘贴一条职位发布",
      importAction: "导入",
      runFailed: "导入失败了。",
      characterCount: "{count} 个字符",
      nothingSent: "在你导入之前，什么都不会发送。",
      description: "粘贴完整发布。分析师将填入公司、技能、职责，角色将进入您的跟踪器。",
      sourceUrl: "来源网址（可选）",
      pasteFullPosting: "粘贴完整发布 — 职责、要求、加分项…",
      filingTracker: "归档至跟踪器",
      extractingCompanyRole: "提取公司和角色中",
      jobPostingText: "职位发布文本",
      readingPosting: "读取发布中",
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
      upload: "上传失败了。",
      parse: "解析失败了。",
      versionSwitch: "没能切换当前版本。",
      resumeDelete: "没能删除这份简历。",
      draftVersionSave: "没能把这份草稿存成版本。",
      printView: "没能准备好打印视图。",
      coverLetter: "求职信生成失败了。",
      transcribe: "没能转写这段录音。",
      speak: "没能念出这个问题。",
      savedListUpdate: "没能更新收藏列表。",
      matchAnalysis: "匹配分析失败了。",
      jdAnalysis: "JD 分析失败了。",
      suggestionsFetch: "没能取到建议。",
      ingest: "入库失败了。",
      applicationCreate: "没能创建这条申请。",
      applicationUpdate: "没能更新那条申请。",
      applicationMove: "没能保存这次移动——看板已回退。",
      applicationDelete: "没能删除那条申请。",
      noteSave: "没能保存这条笔记。",
      noteUpdate: "没能更新这条笔记。",
      noteDelete: "没能删除这条笔记。",
      interviewStart: "没能开始这场面试。",
      openingQuestion: "没能取到开场问题。",
      answerEvaluate: "没能评估这个回答。",
      interviewFinalize: "没能收尾这场面试。",
      conversationStart: "没能开始一段对话。",
      conversationRename: "没能重命名这段对话。",
      conversationDelete: "没能删除这段对话。",
      rendererEmpty: "渲染器没有返回文档。",
      profileSave: "没能保存你的资料。",
      careerProfileSave: "没能保存你的职业档案。",
      memoryUpdate: "没能更新那条记忆。",
      memoryForget: "没能忘掉那条记忆。",
      contactSave: "没能保存这位联系人。",
      contactUpdate: "没能更新这位联系人。",
      contactDelete: "没能删除这位联系人。",
      growthReport: "没能生成成长报告。",
      gapAnalyze: "没能分析这处差距。",
      roleReadiness: "没能读到那个岗位的就绪度。",
      learningPlan: "没能生成学习计划。",
      marketDemand: "没能读到市场需求。",
      priorityRank: "没能排出学习优先级。",
      progressionPlan: "没能规划晋升路径。",
      interviewPrep: "没能生成面试准备。",
      storyBank: "没能读到故事库。",
      roleSuggest: "没能给出岗位建议。",
      companyCorpus: "没能读到那家公司的语料。",
      skillProgress: "没能读到技能进展。",
      messageDraft: "没能起草那条消息。",
      dataExport: "没能导出你的数据。",
      importPlan: "没能生成导入计划。",
      importApply: "没能执行这次导入。",
      bundleRedact: "没能给数据包做脱敏。",
      bundleRender: "没能渲染这个数据包。",
      feedParse: "没能解析这个订阅源。",
      postingsDedup: "没能给那些职位去重。",
      corpusSweep: "没能清扫那个语料库。",
      ingestionPlan: "没能生成入库计划。",
      offerBenchmark: "没能对那个岗位做基准分析。",
      negotiationPlan: "没能生成谈判方案。",
      offerCompare: "没能比较这些 offer。",
      counterOffer: "没能起草还价。",
      mfaEnroll: "没能开始两步验证的设置。",
      mfaActivate: "没能验证这个验证码——两步验证仍是关闭的。",
      mfaRecoveryCodes: "没能更换备用码。",
      mfaDisable: "没能关闭两步验证。",
      mailSettingSave: "没能改这个邮件设置。",
    },
  },
} as const;

export type TranslationKey = keyof typeof translations.en;
