export type NestedDict = { [key: string]: string | NestedDict }

export function translate(
  dict: NestedDict,
  key: string,
  vars?: Record<string, string | number>,
): string {
  const parts = key.split('.')
  let cur: string | NestedDict | undefined = dict
  for (const part of parts) {
    if (typeof cur !== 'object' || cur == null) return key
    cur = cur[part]
  }
  if (typeof cur !== 'string') return key
  if (!vars) return cur
  return cur.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? ''))
}
