import { test, expect } from "@playwright/test";

test("theme toggle cycles and persists across reload", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).not.toHaveAttribute("data-theme", "dark");

  const toggle = page.getByRole("button", { name: /Theme:/ });
  await toggle.click(); // system -> light
  await toggle.click(); // light -> dark
  await expect(html).toHaveAttribute("data-theme", "dark");

  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark");

  // Reset so other tests/runs start from a known state.
  await page.getByRole("button", { name: /Theme:/ }).click();
});

test("command palette opens with Ctrl+K and navigates to new-meeting", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+k");

  const dialog = page.getByRole("dialog", { name: "Command palette" });
  await expect(dialog).toBeVisible();

  await dialog.getByText("New meeting…").click();
  await expect(page).toHaveURL(/\/meetings\/new$/);
});

test("command palette closes on Escape", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toHaveCount(0);
});
