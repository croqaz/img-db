import os from "os";
import path from "path";
import fs from "fs/promises";
import { test } from "bun:test";
import { chromium } from "playwright";
import { expect } from "@playwright/test";

// To test the PyInstaller bin, switch to "./dist/imgdb"
const EXECUTABLE = ["python", "imgdb", "server"];

const tempPath = path.join(os.tmpdir(), `temp-${Date.now()}`);
console.log(`Using temporary path: ${tempPath}`);

async function waitForServer(url: string, timeout = 2500): Promise<boolean> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return true;
      }
    } catch (err) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error(`Server did not start within ${timeout}ms!`);
}

test("create new gallery", async () => {
  const srv = Bun.spawn(EXECUTABLE, {
    stdout: "inherit",
    stderr: "inherit",
    env: {
      ...process.env,
      RECENT_DBS: path.join(tempPath, "recent1.htm"),
      UPLOAD_DIR: path.join(tempPath, "uploads1"),
    },
  });
  srv.unref();
  await waitForServer("http://127.0.0.1:18888");

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto("http://127.0.0.1:18888");

    // Fill the "Create new" form
    const newDbPath = path.join(tempPath, "new-gallery.htm");
    await page.fill("#db-path", newDbPath);

    // Click the "Create" button
    await page.click("button:has-text('Create')");

    // Wait for navigation to the gallery page
    await page.waitForURL(/\/gallery\?db=.*/);

    // Check that we are on the gallery explorer
    await expect(page).toHaveTitle("img-DB Gallery");
    await expect(page.locator("#currentDB")).toContainText(newDbPath);

    // Go back to the home page
    await page.goto("http://127.0.0.1:18888");

    // Click on the gallery link in the "Recently opened" list
    await page.click(`a:has-text("new-gallery.htm")`);

    // Wait for navigation to the gallery page
    await page.waitForURL(/\/gallery\?db=.*/);

    // Check that we are on the gallery explorer again
    await expect(page).toHaveTitle("img-DB Gallery");
    await expect(page.locator("#currentDB")).toContainText(newDbPath);

    // Check that the recent.htm file was created and contains the new gallery
    const recentContent = await Bun.file(
      path.join(tempPath, "recent1.htm"),
    ).text();
    expect(recentContent).toContain("new-gallery.htm");
    expect(recentContent).toContain("0 images");
  } catch (err) {
    console.error("Error during test execution:", err);
  }

  // Cleanup stuff
  srv.kill();
  await browser.close();
  // Give the server time to shut down
  await Bun.sleep(500);
});

test("import into gallery", async () => {
  /*
   * End-to-end test for importing images into a gallery.
   */
  const srv = Bun.spawn(EXECUTABLE, {
    stdout: "inherit",
    stderr: "inherit",
    env: {
      ...process.env,
      RECENT_DBS: path.join(tempPath, "recent2.htm"),
      UPLOAD_DIR: path.join(tempPath, "uploads2"),
    },
  });
  srv.unref();
  await waitForServer("http://127.0.0.1:18888");

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto("http://127.0.0.1:18888");

    // Fill the "Create new" form
    const newDbPath = path.join(tempPath, "import-gallery.htm");
    await page.fill("#db-path", newDbPath);

    // Click the "Create" button
    await page.click("button:has-text('Create')");

    // Wait for navigation to the gallery page
    await page.waitForURL(/\/gallery\?db=.*/);

    // Click the "Import" button
    await page.click("#openImport");

    // Wait for the import modal to be visible
    await expect(page.locator("#import-modal")).toBeVisible();

    // Select images to import
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click("#importBrowse");
    const fileChooser = await fileChooserPromise;

    // Select some images from test/pics/
    await fileChooser.setFiles([
      path.join(__dirname, "pics", "Aldrin_Apollo_11.jpg"),
      path.join(__dirname, "pics", "Claudius_Ptolemy_The_World.png"),
      path.join(__dirname, "pics", "Mona_Lisa_by_Leonardo_da_Vinci.jpg"),
    ]);

    // Click the "Import" button in the modal
    await page.click("#startImport");

    // Wait for the import to finish (modal should close or show success)
    // The page should reload or update with the new images
    await page.waitForFunction(
      () => {
        // @ts-ignore: It's in the page context
        const images = document.querySelectorAll(".gallery-image");
        return images.length === 3;
      },
      { timeout: 2500 },
    );

    // Check that the images are uploaded to UPLOAD_DIR
    const uploadedFiles = await fs.readdir(path.join(tempPath, "uploads2"));
    expect(uploadedFiles).toContain("Aldrin_Apollo_11.jpg");
    expect(uploadedFiles).toContain("Claudius_Ptolemy_The_World.png");
    expect(uploadedFiles).toContain("Mona_Lisa_by_Leonardo_da_Vinci.jpg");

    // Check that the recent.htm file was updated
    const recentContent = await Bun.file(
      path.join(tempPath, "recent2.htm"),
    ).text();
    expect(recentContent).toContain("3 images");
  } catch (err) {
    console.error("Error during test execution:", err);
  }

  // Cleanup stuff
  srv.kill();
  await browser.close();
  // Give the server time to shut down
  await Bun.sleep(500);
});
