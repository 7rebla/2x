// All visible texts of the user interface in one place (English).
// The later translation (German/English) replaces this module's values.

export const texts = {
  appTitle: "2x",
  selftest: {
    heading: "Self-test",
    intro: "Checks the database and the background worker through the API.",
    recheck: "Check again",
    checking: "Checking…",
    statusOk: "OK",
    statusFailed: "Failed",
    errorLabel: "Error",
    apiUnreachable: "The API did not respond. Is the server running?",
    apiHttpError: (status: number): string =>
      `The API answered with HTTP status ${String(status)}.`,
    apiInvalidAnswer: "The API sent an answer this page cannot read.",
    unexpectedError: "The self-test could not be run in this browser. Please try again.",
    database: {
      heading: "Database",
      serverVersion: "Server version",
    },
    worker: {
      heading: "Worker",
      result: "Result",
      duration: "Duration",
      durationValue: (milliseconds: number): string =>
        `${String(milliseconds)} ms`,
    },
  },
} as const;
