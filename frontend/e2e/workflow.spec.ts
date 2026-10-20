import { expect, test } from "@playwright/test";

test("import a synthetic audit and compare groups", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("generate-similar_accuracy_different_errors").click();
  await expect(page.getByRole("heading", { name: /Similar accuracy/ })).toBeVisible();
  await page.getByRole("button", { name: "Run audit" }).click();
  await expect(page.getByTestId("confusion-matrix")).toBeVisible();
  await expect(page.getByText("TN").first()).toBeVisible();
  await page.getByRole("link", { name: "Group disparities" }).click();
  await expect(page.getByTestId("group-card-group_a")).toContainText("n = 100");
  await expect(page.getByTestId("group-card-group_b")).toContainText("0.0%");
  await expect(page.getByTestId("group-card-group_c")).toContainText("n = 4");
  await expect(page.getByTestId("group-card-group_c")).toContainText("not a zero");
  await expect(page.getByTestId("cannot-conclude")).toContainText("do not certify");
});
