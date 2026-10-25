import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
const password = "synthetic-browser-test-only";
test("R2F worksheet mode, reinspection and mapping match the imported workbook", async ({
  page,
}, info) => {
  const file = info.outputPath("synthetic-sheets.xlsx");
  mkdirSync(dirname(file), { recursive: true });
  const python = resolve(
    "..",
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  execFileSync(python, [
    "-c",
    "from openpyxl import Workbook; import sys; b=Workbook(); s=b.active; s.title='First'; [s.append(r) for r in [['Identifier','Description','Balance'],['000011','First item','2'],['TOTAL','','2']]]; s=b.create_sheet('Second'); [s.append(r) for r in [['quantity','barcode','name'],['99','000022','Second item'],['99','','TOTAL']]]; b.save(sys.argv[1])",
    file,
  ]);
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /إنشاء الحساب المحلي|دخول مساحة العمل/ }),
  ).toBeVisible();
  const setup = page.getByLabel("عيّن كلمة مرور المالك");
  if (await setup.count()) {
    await setup.fill(password);
    await page.getByRole("button", { name: "إنشاء الحساب المحلي" }).click();
  } else {
    await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
    await page.getByRole("button", { name: "دخول مساحة العمل" }).click();
  }
  await page
    .getByRole("button", { name: "استيراد ومراجعة", exact: true })
    .click();
  await page.locator('input[name="scope"]').fill("r2f-sheets");
  await page.locator('input[name="start"]').fill("2022-01-31");
  await page.locator('input[name="file"]').setInputFiles(file);
  await expect(page.getByLabel("كل أوراق الملف")).toBeChecked();
  await expect(page.getByLabel("قراءة ورقة First")).toBeChecked();
  await expect(page.getByLabel("قراءة ورقة Second")).toBeChecked();
  await page.getByLabel("أوراق مختارة فقط").check();
  await page.getByLabel("قراءة ورقة First").check();
  await page.getByLabel("قراءة ورقة First").uncheck();
  const submit = page.getByRole("button", { name: "استخراج وتجهيز المراجعة" });
  await expect(submit).toBeDisabled();
  await expect(page.getByLabel("أوراق مختارة فقط")).toBeChecked();
  await page.getByLabel("قراءة ورقة First").check();
  const reinspect = page.getByRole("button", {
    name: "إعادة فحص الملف بالخيارات الحالية",
  });
  await reinspect.click();
  const inspection = page.getByRole("region", { name: "فحص الملف" });
  await expect(inspection.getByText("000011", { exact: true })).toBeVisible();
  await expect(inspection.getByText("000022", { exact: true })).toHaveCount(0);
  await inspection.getByLabel("تعيين الباركود").selectOption("Identifier");
  await inspection.getByLabel("تعيين اسم الصنف").selectOption("Description");
  await inspection.getByLabel("تعيين الكمية").selectOption("Balance");
  await reinspect.click();
  await expect(page.getByLabel("قراءة ورقة First")).toBeChecked();
  await expect(inspection.getByLabel("تعيين الباركود")).toHaveValue(
    "Identifier",
  );
  await page.getByText("خيارات الأعمدة والترميز", { exact: true }).click();
  const mapping = page.locator('textarea[name="mapping"]');
  await mapping.fill('{"barcode":');
  await expect(submit).toBeDisabled();
  await expect(inspection.getByLabel("تعيين الباركود")).toHaveValue("");
  await mapping.fill(
    '{"barcode":"Identifier","name":"Description","quantity":"Balance"}',
  );
  await page.locator('input[name="complete"]').check();
  await submit.click();
  await expect(
    page.getByRole("button", { name: "قبول البيانات" }),
  ).toBeEnabled();
  const staged = (await (await page.request.get("/api/batches")).json()).find(
    (item: { scope: string }) => item.scope === "r2f-sheets",
  );
  const persisted = await (
    await page.request.get(`/api/batches/${staged.id}`)
  ).json();
  expect(persisted.metadata.sheet_mode).toBe("selected");
  expect(persisted.metadata.sheets).toEqual(["First"]);
  expect(
    persisted.rows
      .filter((row: { kind: string }) => row.kind === "detail")
      .map(
        (row: { raw: { location: { sheet: string } } }) =>
          row.raw.location.sheet,
      ),
  ).toEqual(["First"]);
  await page.getByRole("button", { name: "قبول البيانات" }).click();
  await page.getByRole("button", { name: "نظرة عامة", exact: true }).click();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("2.00");
  const batches = await (await page.request.get("/api/batches")).json();
  const batch = batches.find(
    (item: { scope: string }) => item.scope === "r2f-sheets",
  );
  await page.request.post(`/api/batches/${batch.id}/action`, {
    headers: { "X-Requested-With": "Madrid" },
    data: { action: "rollback", reason: "isolated worksheet selection check" },
  });
});
test("R2 unknown CSV is inspected, mapped, reconciled, accepted and remains scoped after reload", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /إنشاء الحساب المحلي|دخول مساحة العمل/ }),
  ).toBeVisible();
  const setup = page.getByLabel("عيّن كلمة مرور المالك");
  if (await setup.count()) {
    await setup.fill(password);
    await page.getByRole("button", { name: "إنشاء الحساب المحلي" }).click();
  } else {
    await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
    await page.getByRole("button", { name: "دخول مساحة العمل" }).click();
  }
  await page
    .getByRole("button", { name: "استيراد ومراجعة", exact: true })
    .click();
  await page.locator('input[name="start"]').fill("2021-05-31");
  const batchesBefore = (await (await page.request.get("/api/batches")).json())
    .length;
  await page.locator('input[name="scope"]').fill("r2-mapping");
  await page.locator('input[name="file"]').setInputFiles({
    name: "unknown.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      'Identifier,Description,Balance\n000077,"تي شيرت, Basic",7\nTOTAL,,7\n',
    ),
  });
  const inspection = page.getByRole("region", { name: "فحص الملف" });
  await expect(
    inspection.getByRole("heading", { name: /يحتاج تعيين/ }),
  ).toBeVisible();
  await expect(inspection.getByText("000077", { exact: true })).toBeVisible();
  expect((await (await page.request.get("/api/batches")).json()).length).toBe(
    batchesBefore,
  );
  await inspection.getByLabel("تعيين الباركود").selectOption("Identifier");
  await inspection.getByLabel("تعيين اسم الصنف").selectOption("Description");
  await inspection.getByLabel("تعيين الكمية").selectOption("Balance");
  await page.locator('input[name="complete"]').check();
  await page.getByRole("button", { name: "استخراج وتجهيز المراجعة" }).click();
  await expect(
    page.getByRole("button", { name: "قبول البيانات" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "قبول البيانات" }).click();
  await page.getByRole("button", { name: "نظرة عامة", exact: true }).click();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("7.00");
  await page.reload();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("7.00");
  const csv = await page.request.get(
    "/api/exports/csv?start=2021-05-31&end=2021-05-31&stock_asof=2021-05-31&scope=r2-mapping",
  );
  expect(csv.ok()).toBeTruthy();
  expect(await csv.text()).toContain("000077");
  // Remove contribution through the public audited action so subsequent journeys start empty.
  const batches = await (await page.request.get("/api/batches")).json();
  const batch = batches.find(
    (item: { scope: string }) => item.scope === "r2-mapping",
  );
  await page.request.post(`/api/batches/${batch.id}/action`, {
    headers: { "X-Requested-With": "Madrid" },
    data: { action: "rollback", reason: "isolated R2 browser verification" },
  });
});
test("owner reviews import, reconciles, accepts, reuploads, exports, rolls back and uses mobile PWA", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: /إنشاء الحساب المحلي|دخول مساحة العمل/ }),
  ).toBeVisible();
  const setup = page.getByLabel("عيّن كلمة مرور المالك");
  if (await setup.count()) {
    await setup.fill(password);
    await page.getByRole("button", { name: "إنشاء الحساب المحلي" }).click();
  } else {
    await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
    await page.getByRole("button", { name: "دخول مساحة العمل" }).click();
  }
  await expect(
    page.getByRole("heading", { name: "الصورة الكاملة لمحلك" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "أول قرار بيبدأ بتقرير" }),
  ).toBeVisible();
  await page.getByLabel("بداية فترة التحليل").fill("2026-10-01");
  await page.getByLabel("نهاية فترة التحليل").fill("2026-10-24");
  await page.getByRole("button", { name: "تحديث النتائج" }).click();
  await page
    .getByRole("button", { name: "استيراد تقرير", exact: true })
    .click();
  const csv =
    "barcode,name,category,quantity,reserved,available\n000366,منتج تجريبي,ملابس,10,2,8\nTOTAL,,,10,2,8\n";
  await page.locator('input[name="start"]').fill("2026-10-24");
  await page.locator('input[name="end"]').fill("2026-10-24");
  await page.locator('input[name="file"]').setInputFiles({
    name: "synthetic.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.locator('input[name="complete"]').check();
  await page.locator('input[name="reservation_verified"]').check();
  await page.getByRole("button", { name: "استخراج وتجهيز المراجعة" }).click();
  const review = page.getByRole("region", { name: "مراجعة الدفعة" });
  await expect(
    page.getByRole("heading", { name: /مراجعة: synthetic.csv/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "قبول البيانات" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "قبول البيانات" }).click();
  await expect(
    page.getByRole("button", { name: "تراجع موثق عن الدفعة" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "نظرة عامة", exact: true }).click();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("10.00");
  await expect(page.getByText("000366", { exact: true })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "XLSX", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  await page
    .getByRole("button", { name: "استيراد ومراجعة", exact: true })
    .click();
  // Navigation remounts the form. Actually select the identical source again;
  // the persisted accepted review alone is not proof of a successful reupload.
  await page
    .locator('input[name="file"]')
    .setInputFiles({
      name: "synthetic.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
  await page.locator('input[name="complete"]').check();
  await page.locator('input[name="reservation_verified"]').check();
  const reupload = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/imports") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "استخراج وتجهيز المراجعة" }).click();
  const repeated = await reupload;
  expect(repeated.ok()).toBeTruthy();
  expect((await repeated.json()).status).toBe("accepted");
  await expect(
    page.getByRole("button", { name: "تراجع موثق عن الدفعة" }),
  ).toBeVisible();
  const list = await page.request.get("/api/batches");
  expect(
    (await list.json()).filter(
      (batch: { scope: string }) => batch.scope === "store",
    ).length,
  ).toBe(1);
  const snapshot = await page.request.get(
    "/api/exports/pdf?start=2026-10-01&end=2026-10-24",
  );
  expect(snapshot.ok()).toBeTruthy();
  expect((await snapshot.body()).subarray(0, 5).toString()).toBe("%PDF-");
  await page.screenshot({ path: "test-results/desktop.png", fullPage: true });
  await page.setViewportSize({ width: 360, height: 800 });
  await page.getByRole("button", { name: "فتح القائمة" }).click();
  await page
    .getByRole("button", { name: "المخزون والمنتجات", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "كل منتج، والصورة وراه" }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "ابحث عن منتج" }).fill("000366");
  await expect(page.getByRole("table")).toContainText("منتج تجريبي");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
  const manifest = await page.request.get("/manifest.webmanifest");
  expect((await manifest.json()).display).toBe("standalone");
  await page.evaluate(() => navigator.serviceWorker.ready);
  const cached = await page.evaluate(async () => {
    const keys = await caches.keys();
    const urls: string[] = [];
    for (const key of keys) {
      const c = await caches.open(key);
      for (const req of await c.keys()) urls.push(req.url);
    }
    return urls;
  });
  expect(cached.some((u) => u.includes("/api/"))).toBe(false);
  await page.getByRole("button", { name: "فتح القائمة" }).click();
  await page
    .getByRole("button", { name: "استيراد ومراجعة", exact: true })
    .click();
  page.once("dialog", (d) => d.accept("synthetic rollback evidence"));
  await page.getByRole("button", { name: "تراجع موثق عن الدفعة" }).click();
  await expect(
    page.getByText("تم التراجع", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "فتح القائمة" }).click();
  await page.getByRole("button", { name: "تسجيل الخروج" }).click();
  await expect(
    page.getByRole("button", { name: "دخول مساحة العمل" }),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  expect(await page.locator(":focus").count()).toBe(1);
  expect(errors).toEqual([]);
});

test("PWA installability is verified in a normal persistent profile", async ({
  playwright,
}, testInfo) => {
  const context = await playwright.chromium.launchPersistentContext(
    testInfo.outputPath("pwa-profile"),
    {
      ...(process.env.MADRID_BROWSER
        ? { executablePath: process.env.MADRID_BROWSER }
        : {}),
      headless: true,
    },
  );
  try {
    const page = await context.newPage();
    await page.goto("http://127.0.0.1:8123/");
    await page.evaluate(() => navigator.serviceWorker.ready);
    const cdp = await context.newCDPSession(page);
    await cdp.send("Page.enable");
    const result = await cdp.send("Page.getInstallabilityErrors");
    expect(result.installabilityErrors).toEqual([]);
  } finally {
    await context.close();
  }
});

test("accepted stock and sales update the same products, dates and recommendations on demand", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
  await page.getByRole("button", { name: "دخول مساحة العمل" }).click();
  await expect(
    page.getByRole("heading", { name: "الصورة الكاملة لمحلك" }),
  ).toBeVisible();
  const scope = "dynamic-browser-check";
  const stock =
    "barcode,name,quantity,reserved,available\n000501,First item,10,0,10\n000502,Second item,5,0,5\nTOTAL,,15,0,15\n";
  const sales =
    "barcode,name,sold,returned\n000501,Same barcode different display name,10,4\nTOTAL,,10,4\n";
  async function importFile(kind: string, name: string, content: string) {
    await page
      .getByRole("button", { name: "استيراد ومراجعة", exact: true })
      .click();
    await page.locator('select[name="type"]').selectOption(kind);
    await page
      .locator('input[name="start"]')
      .fill(kind === "snapshot" ? "2020-09-30" : "2020-09-01");
    await page.locator('input[name="end"]').fill("2020-09-30");
    await page.locator('input[name="scope"]').fill(scope);
    await page.locator('input[name="file"]').setInputFiles({
      name,
      mimeType: "text/csv",
      buffer: Buffer.from(content),
    });
    await page.locator('input[name="complete"]').check();
    await page.locator('input[name="reservation_verified"]').check();
    await page.getByRole("button", { name: "استخراج وتجهيز المراجعة" }).click();
    await expect(
      page.getByRole("heading", { name: `مراجعة: ${name}` }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "قبول البيانات" }),
    ).toBeEnabled();
  }
  await importFile("snapshot", "dynamic-stock.csv", stock);
  await expect(
    page.getByText(
      /لا يدخل في المخزون أو المبيعات والتحليل إلا بعد قبول البيانات/,
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "قبول البيانات" }).click();
  await page
    .getByRole("button", { name: "عرض التحليل والنصائح المحدثة" })
    .click();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("15.00");
  await expect(page.getByLabel("نهاية فترة التحليل")).toHaveValue("2020-09-30");
  await importFile("sales", "dynamic-sales.csv", sales);
  await expect(
    page.getByLabel("مطابقة الملف مع البيانات الموجودة"),
  ).toContainText("1 صنف موجود بنفس الباركود");
  await page.getByRole("button", { name: "قبول البيانات" }).click();
  await page
    .getByRole("button", { name: "عرض التحليل والنصائح المحدثة" })
    .click();
  await expect(page.getByLabel("بداية فترة التحليل")).toHaveValue("2020-09-01");
  await expect(
    page.getByText("افحص أسباب المرتجعات", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("راجع عرض المنتج والطلب عليه", { exact: true }),
  ).toBeVisible();
  const count = (await (await page.request.get("/api/batches")).json()).filter(
    (batch: { scope: string }) => batch.scope === scope,
  ).length;
  expect(count).toBe(2);
  await page.getByLabel("نهاية فترة التحليل").fill("2020-10-01");
  await expect(
    page.getByText("افحص أسباب المرتجعات", { exact: true }),
  ).toBeVisible();
  expect(
    await page
      .getByRole("link", { name: "CSV", exact: true })
      .getAttribute("href"),
  ).toContain("end=2020-09-30");
  await page.getByRole("button", { name: "تحديث النتائج" }).click();
  await expect(
    page.getByText("افحص أسباب المرتجعات", { exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel("نهاية فترة التحليل")).toHaveValue("2020-09-30");
  await expect(
    page.getByText("افحص أسباب المرتجعات", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".metric-card").filter({ hasText: "رصيد المخزون" }),
  ).toContainText("15.00");
});
