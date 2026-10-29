/** A backend call failed; `message` is safe to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** The caller cancelled the request (new conversation, stop button). Not an error to show. */
export class CancelledError extends ApiError {
  constructor() {
    super("Request cancelled");
    this.name = "CancelledError";
  }
}

export function isCancelled(error: unknown): boolean {
  return error instanceof CancelledError;
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
