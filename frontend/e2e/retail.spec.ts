import { test, expect } from "@playwright/test";
const password = "synthetic-browser-test-only";
test("owner reviews import, reconciles, accepts, reuploads, exports, rolls back and uses mobile PWA", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("عيّن كلمة مرور المالك").fill(password);
  await page.getByRole("button", { name: "إنشاء الحساب المحلي" }).click();
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
  await page.getByRole("button", { name: "استخراج وتجهيز المراجعة" }).click();
  await expect(
    page.getByRole("button", { name: "تراجع موثق عن الدفعة" }),
  ).toBeVisible();
  const list = await page.request.get("/api/batches");
  expect((await list.json()).length).toBe(1);
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
      executablePath: process.env.MADRID_BROWSER || "/usr/bin/chromium",
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
