export function buildProductI18nFields({
  nameEn,
  nameHe,
  extraNames,
  extraLangs,
  descriptionEn,
  descriptionHe,
  extraDescs,
  copyFallbacks,
}: {
  nameEn: string
  nameHe?: string
  extraNames: Record<string, string>
  extraLangs: string[]
  descriptionEn?: string
  descriptionHe?: string
  extraDescs: Record<string, string>
  copyFallbacks: boolean
}): { name: Record<string, string>; description?: Record<string, string> } {
  const heName = nameHe?.trim() || (copyFallbacks ? nameEn : '')
  const name: Record<string, string> = { en: nameEn, he: heName }
  for (const lang of extraLangs) {
    name[lang] = extraNames[lang]?.trim() || (copyFallbacks ? (heName || nameEn) : '')
  }

  const descriptionEnTrim = descriptionEn?.trim() || ''
  const descriptionHeTrim = descriptionHe?.trim() || (copyFallbacks ? descriptionEnTrim : '')
  const hasAnyDesc = Boolean(
    descriptionEnTrim || descriptionHeTrim || extraLangs.some((lang) => extraDescs[lang]?.trim()),
  )
  if (!hasAnyDesc && copyFallbacks) {
    return { name }
  }

  const description: Record<string, string> = { en: descriptionEnTrim, he: descriptionHeTrim }
  for (const lang of extraLangs) {
    description[lang] = extraDescs[lang]?.trim() || (copyFallbacks ? (descriptionHeTrim || descriptionEnTrim) : '')
  }
  return { name, description }
}
