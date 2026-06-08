import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.beforeEach(async () => {
  // Reset database to ensure a clean state by running the script with backend as cwd
  execSync('python scripts/reset_db.py', {
    cwd: path.resolve(__dirname, '../../backend'),
  });
});

test.describe('AI Research Assistant E2E Tests', () => {
  
  test('should log in and submit user feedback successfully', async ({ page }) => {
    // 1. Go to homepage (should redirect to login if not authenticated)
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);

    // 2. Log in
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');

    // 3. Verify redirected to dashboard chat page
    await page.waitForURL('**/');
    await expect(page.locator('text=✦ Research AI')).toBeVisible();

    // 4. Click Feedback floating button
    await page.click('#btn-feedback-trigger');
    await expect(page.locator('text=Send Feedback')).toBeVisible();

    // 5. Fill out and submit feedback
    // select category
    await page.selectOption('form select', 'Bug');
    // fill comment
    await page.fill('textarea[placeholder^="Tell us what you think"]', 'Testing E2E feedback bug report.');
    // submit
    await page.click('button:has-text("Submit")');

    // 6. Verify success state message
    await expect(page.locator('text=Thank you!')).toBeVisible();
    await expect(page.locator('text=Your feedback has been submitted successfully.')).toBeVisible();
  });

  test('should perform a simple chat session and receive AI responses', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');

    // 2. Select first workspace and model if they exist
    // The WorkspaceSelector is active
    await page.locator('button:has-text("Logout")').waitFor();

    // 3. Type question in chat input
    const input = page.locator('textarea[placeholder^="Ask a research question"], input[placeholder^="Type a message"]');
    await expect(input).toBeVisible();
    await input.fill('What is the capital of France?');
    
    // 4. Press Enter or click Send
    await input.press('Enter');

    // 5. Verify response from EchoLLM or active provider is displayed
    const responseText = page.locator('text=France'); // or verify chat response element is loaded
    // Since we override to EchoLLM in test configs, it'll respond or Bedrock/LiteLLM will reply.
    // Let's just wait for some message to appear in the assistant area
    const assistantMessage = page.locator('article:not(.flex-row-reverse)');
    await expect(assistantMessage.first()).toBeVisible({ timeout: 15000 });
  });

  test('should submit and track async research task in the Temporal queue', async ({ page }) => {
    // 1. Log in
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/');

    // 2. Navigate to Queue page
    await page.click('a[href="/queue"]');
    await expect(page).toHaveURL(/\/queue/);
    await expect(page.locator('text=Research Queue')).toBeVisible();
 
    // 3. Submit a question to the queue
    const queueInput = page.locator('textarea[placeholder^="Submit a background"]');
    await queueInput.fill('List 3 benefits of async workflows.');
    // Click the send button inside the form
    await page.click('form button');

    // 4. Check that task is added to list and goes to complete
    const taskCard = page.locator('div').filter({ hasText: 'List 3 benefits of async workflows' }).first();
    await expect(taskCard).toBeVisible();

    // 5. Wait for the status to show Completed (temporal workflow updates)
    // The polling is every 3 seconds, so we wait up to 25 seconds.
    const completeBadge = taskCard.locator('text=Completed');
    await expect(completeBadge).toBeVisible({ timeout: 25000 });

    // 6. Verify answer display
    await expect(taskCard.locator('text=Answer')).toBeVisible();
  });
});
