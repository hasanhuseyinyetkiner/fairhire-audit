import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const outDir = path.resolve("..", "docs", "screenshots");

test("capture light and dark audit screens", async ({ page }) => {
  mkdirSync(outDir, { recursive: true });
  const listed = await page.request.get("/api/datasets");
  expect(listed.ok()).toBeTruthy();
  const body = (await listed.json()) as {
    datasets: Array<{ synthetic_profile: string | null; latest_audit_id: string | null }>;
  };
  const dataset = body.datasets.find(
    (item) => item.synthetic_profile === "similar_accuracy_different_errors" && item.latest_audit_id,
  );
  expect(dataset?.latest_audit_id).toBeTruthy();
  const auditId = dataset!.latest_audit_id!;

  async function shoot(theme: "light" | "dark", route: string, name: string) {
    await page.goto("/");
    await page.evaluate((value) => localStorage.setItem("fairhire-theme", value), theme);
    await page.goto(`/audits/${auditId}/${route}`);
    await expect(page.getByTestId("cannot-conclude")).toBeVisible();
    await page.screenshot({ path: path.join(outDir, `${name}-${theme}.png`) });
  }

  await shoot("light", "groups", "group-disparities");
  await shoot("dark", "groups", "group-disparities");
  await shoot("light", "quality", "model-quality");
  await shoot("dark", "quality", "model-quality");
  await shoot("light", "report", "audit-report");
  await shoot("dark", "report", "audit-report");
});
