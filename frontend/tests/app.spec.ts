import { expect, test } from "@playwright/test";

test("login page exposes product entry point", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Понимайте, как AI видит ваш бренд" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});
