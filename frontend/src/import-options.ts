export type SheetMode = "all" | "selected";
export type ParserOptions = {
  encoding: string;
  delimiter: string;
  pdf_profile: string;
};

export function parseMapping(text: string): Record<string, string> {
  const value: unknown = JSON.parse(text);
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.entries(value).some(
      ([key, entry]) =>
        !/^[a-z_]+$/.test(key) || typeof entry !== "string" || !entry.trim(),
    )
  )
    throw new Error(
      "تعيين الأعمدة لازم يكون كائن JSON بأسماء حقول وقيم نصية غير فارغة",
    );
  return value as Record<string, string>;
}

export function selectedSheets(text: string, mode: SheetMode): string[] {
  if (mode === "all") return [];
  const names = [
    ...new Set(text.split(/\r?\n/).filter((name) => name.length > 0)),
  ];
  if (!names.length)
    throw new Error("اختار ورقة واحدة على الأقل أو اختار كل الأوراق صراحةً");
  return names;
}
