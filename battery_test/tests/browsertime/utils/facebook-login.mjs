import { CREDENTIALS } from "../config/credentials.mjs";

export async function loginToFacebook(driver, commands, By, until) {
  console.log("Logging into Facebook.");
  await commands.wait.byTime(5000);

  try {
    await enterLoginCredentials(driver, By);
    await commands.wait.byTime(5000);
    await clickLoginButton(driver, By);
    await commands.wait.byTime(5000);
    await handleNotNowDialog(driver, By, until, commands);
    await commands.wait.byTime(5000);
  } catch (error) {
    console.error("Error during Facebook login:", error);
  }
}

async function enterLoginCredentials(driver, By) {
  const emailField = await driver.findElement(By.id("m_login_email"));
  const passField = await driver.findElement(By.id("m_login_password"));

  await emailField.clear();
  await emailField.sendKeys(CREDENTIALS.facebook.email);

  await passField.clear();
  await passField.sendKeys(CREDENTIALS.facebook.password);
}

async function clickLoginButton(driver, By) {
  const loginButton = await driver.findElement(By.css('[aria-label="Log in"]'));
  await loginButton.click();
}

async function handleNotNowDialog(driver, By, until, commands) {
  await driver.wait(
    until.elementLocated(By.css('div[role="button"][aria-label="Not now"]')),
    5000,
  );
  const notNowButton = await driver.findElement(
    By.css('div[role="button"][aria-label="Not now"]'),
  );
  await notNowButton.click();
  await notNowButton.click();
  await commands.wait.byPageToComplete();
}
