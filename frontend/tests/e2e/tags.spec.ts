import { test, expect } from "@playwright/test";

/** Tags bonus feature (Milestone 12) — add via the input on the meeting
 * detail page, confirm the chip renders, confirm it survives a reload
 * (i.e. it was actually persisted server-side, not just local state). */
test("adding a tag persists across reload", async ({ page }) => {
  const tagName = `e2e-${Date.now()}`;
  await page.goto("/meetings/1");

  const input = page.getByPlaceholder("+ tag");
  await input.fill(tagName);
  await input.press("Enter");

  // The chip's own text content is "<name>✕" (the remove button's glyph is
  // part of the same element), so an exact match on the bare name never
  // matches — a substring match is correct here since the timestamp-based
  // name is unique on the page.
  await expect(page.getByText(tagName)).toBeVisible();

  await page.reload();
  await expect(page.getByText(tagName)).toBeVisible();

  // Clean up so repeated runs don't accumulate tags forever.
  const chip = page.locator("span", { hasText: tagName });
  await chip.hover();
  await chip.getByRole("button", { name: `Remove tag ${tagName}` }).click();
  await expect(page.getByText(tagName)).toHaveCount(0);
});
