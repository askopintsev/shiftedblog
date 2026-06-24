import { expect, test } from "@playwright/test";

test.describe("Editor SPA smoke", () => {
  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Shifted Blog Editor" })).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Пароль")).toBeVisible();
  });

  test("unauthenticated users redirect to login from posts", async ({ page }) => {
    await page.goto("/posts");
    await expect(page).toHaveURL(/\/login/);
  });
});
