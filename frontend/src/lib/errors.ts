// Every catch block in this app used to be typed `catch (err: any)` just to
// read `err.message` -- this is the same behavior (undefined for anything
// that isn't an Error, e.g. a thrown string) without the `any`.
export function errorMessage(err: unknown): string | undefined {
  return err instanceof Error ? err.message : undefined
}
