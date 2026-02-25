import { test, expect } from "@playwright/test";

test.describe("OSINT Pipeline Funnel", () => {
  test("Dashboard loads correctly", async ({ page }) => {
    await page.goto("/");
    
    // Check title
    await expect(page.getByText("Command Center")).toBeVisible();
    
    // Check navigation cards exist
    await expect(page.getByText("Downloads")).toBeVisible();
    await expect(page.getByText("Processing")).toBeVisible();
    await expect(page.getByText("Analysis")).toBeVisible();
    await expect(page.getByText("Settings")).toBeVisible();
    
    // Check quick start guide
    await expect(page.getByText("Quick Start")).toBeVisible();
  });

  test("Ingest page has required elements", async ({ page }) => {
    await page.goto("/ingest");
    
    // Check page title
    await expect(page.getByText("Ingest & Download Manager")).toBeVisible();
    
    // Check URL input textarea exists
    await expect(page.getByLabel("Add URLs")).toBeVisible();
    
    // Check control buttons exist
    await expect(page.getByRole("button", { name: "Add URLs" })).toBeVisible();
    
    // Note: Start Queue button may not be visible initially if queue isn't running
    await expect(page.getByText("Download Ledger")).toBeVisible();
  });

  test("Navigate through the funnel", async ({ page }) => {
    // Start at dashboard
    await page.goto("/");
    await expect(page.getByText("Command Center")).toBeVisible();
    
    // Navigate to Ingest
    await page.click("text=Downloads");
    await expect(page).toHaveURL("/ingest");
    await expect(page.getByText("Ingest & Download Manager")).toBeVisible();
    
    // Navigate to Process
    await page.click("text=Processing");
    await expect(page).toHaveURL("/process");
    await expect(page.getByText("Processing Queue")).toBeVisible();
    
    // Navigate to Analyze
    await page.click("text=Analysis");
    await expect(page).toHaveURL("/analyze");
    await expect(page.getByText("Analysis & Knowledge Graph")).toBeVisible();
    
    // Check Awaken Swarm button exists
    await expect(page.getByRole("button", { name: "Awaken Swarm" })).toBeVisible();
    
    // Navigate to Settings
    await page.click("text=Settings");
    await expect(page).toHaveURL("/settings");
    await expect(page.getByText("Settings")).toBeVisible();
  });

  test("Analyze page has swarm controls", async ({ page }) => {
    await page.goto("/analyze");
    
    // Check swarm control elements
    await expect(page.getByText("Agent Swarm")).toBeVisible();
    await expect(page.getByRole("button", { name: "Awaken Swarm" })).toBeVisible();
    
    // Check audit trail section
    await expect(page.getByText("Audit Trail")).toBeVisible();
    
    // Check graph explorer section
    await expect(page.getByText("Knowledge Graph Explorer")).toBeVisible();
  });

  test("Settings page has model configuration", async ({ page }) => {
    await page.goto("/settings");
    
    // Check page title
    await expect(page.getByText("Configure models and concurrency limits")).toBeVisible();
    
    // Check model selection section
    await expect(page.getByText("Model Selection")).toBeVisible();
    
    // Check OpenRouter API key field
    await expect(page.getByLabel("OpenRouter API Key")).toBeVisible();
    
    // Check concurrency section
    await expect(page.getByText("Concurrency Limits")).toBeVisible();
    
    // Check save button
    await expect(page.getByRole("button", { name: "Save Settings" })).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("sidebar navigation works", async ({ page }) => {
    await page.goto("/");
    
    // Click each nav item and verify URL
    const navItems = [
      { label: "Dashboard", href: "/" },
      { label: "Ingest", href: "/ingest" },
      { label: "Processing", href: "/process" },
      { label: "Analysis", href: "/analyze" },
      { label: "Settings", href: "/settings" },
    ];
    
    for (const item of navItems) {
      await page.click(`text=${item.label}`);
      await expect(page).toHaveURL(item.href);
    }
  });
});
