import { expect, test } from "@playwright/test";

test("import a synthetic audit, compare groups, and export the report", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("generate-similar_accuracy_different_errors").click();
  await expect(page.getByRole("heading", { name: /Similar accuracy/ })).toBeVisible();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();
  await expect(page.getByTestId("cm-tn")).toContainText("91");
  await expect(page.getByTestId("cm-tp")).toContainText("71");
  await page.getByRole("link", { name: "Group disparities" }).click();
  await expect(page.getByTestId("group-card-group_a")).toContainText("n = 100");
  await expect(page.getByTestId("group-card-group_b")).toContainText("0.0%");
  await expect(page.getByTestId("group-card-group_c")).toContainText("n = 4");
  await expect(page.getByTestId("group-card-group_c")).toContainText("not a zero");
  await expect(page.getByTestId("cannot-conclude")).toContainText("do not certify");
  await page.getByRole("link", { name: "Audit report" }).click();
  await expect(page.getByRole("heading", { name: /record of the evidence/i })).toBeVisible();
  const html = page.getByRole("link", { name: "Download HTML" });
  const json = page.getByRole("link", { name: "Download JSON" });
  await expect(html).toBeVisible();
  await expect(json).toBeVisible();
  const htmlHref = await html.getAttribute("href");
  expect(htmlHref).toMatch(/\/api\/audits\/.+\/report\.html$/);
  const report = await page.request.get(htmlHref!);
  expect(report.ok()).toBeTruthy();
  const body = await report.text();
  expect(body).toContain("What this cannot conclude");
  expect(body).toContain("Not a certificate");
  expect(body.toLowerCase()).not.toContain("bias-free");
});

test("threshold lab live metrics and network-fail stale error UX", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("generate-similar_accuracy_different_errors").click();
  await expect(page.getByRole("heading", { name: /Similar accuracy/ })).toBeVisible();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();

  await page.getByRole("link", { name: "Threshold lab" }).click();
  await expect(page.getByRole("heading", { name: /Simulate a cutoff/i })).toBeVisible();
  await expect(page.getByTestId("threshold-methodology")).toBeVisible();
  await expect(page.getByTestId("methodology-version")).not.toHaveText("—");
  await expect(page.getByTestId("null-not-zero")).toContainText(/not zeros/i);

  await expect(page.getByTestId("threshold-slider")).toBeVisible();
  await page.getByTestId("threshold-value").fill("0.7");
  await expect(page.getByTestId("threshold-results")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("threshold-results")).toContainText(/Point estimates only/i);

  // Network-fail path: abort threshold scenario posts and assert alert UX.
  await page.route("**/api/audits/*/threshold-scenarios", async (route) => {
    await route.abort("failed");
  });
  await page.getByTestId("threshold-value").fill("0.3");
  await expect(page.getByRole("alert")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("alert")).toContainText(/failed|Network|Failed|error/i);

  // Recovery: allow traffic again; a newer mutate clears the error via onMutate + success.
  await page.unroute("**/api/audits/*/threshold-scenarios");
  await page.getByTestId("threshold-value").fill("0.55");
  await expect(page.getByTestId("threshold-results")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("accessibility smoke: skip link present, labeled threshold controls, keyboard focus", async ({
  page,
}) => {
  await page.goto("/");
  const skip = page.getByRole("link", { name: /Skip to content/i });
  await expect(skip).toBeAttached();
  await expect(skip).toHaveAttribute("href", "#main");

  await page.getByTestId("generate-similar_accuracy_different_errors").click();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();
  await expect(page.locator("#main")).toBeVisible();

  await page.getByRole("link", { name: "Threshold lab" }).click();
  const slider = page.getByRole("slider", { name: /Decision threshold/i });
  await expect(slider).toBeVisible();
  await slider.focus();
  await expect(slider).toBeFocused();
  await page.keyboard.press("ArrowRight");
  const value = page.getByLabel("Threshold value");
  await expect(value).toBeVisible();
  await value.focus();
  await expect(value).toBeFocused();
});
