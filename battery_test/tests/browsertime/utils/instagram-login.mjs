export async function loginToInstagram(driver, commands, By) {
  await clickInitialLogin(driver, By);
  await commands.wait.byTime(5000);
  await tryFacebookLogin(driver, commands, By);
  await commands.wait.byTime(5000);
}

async function clickInitialLogin(driver, By) {
  const loginButton = await driver.findElement(
    By.xpath('//button[.//div[contains(text(), "Log in")]]'),
  );
  await loginButton.click();
}

async function tryFacebookLogin(driver, commands, By) {
  try {
    await tryDirectFacebookLogin(driver, By);
  } catch (error) {
    await tryForgotPasswordFlow(driver, commands, By);
  }
}

async function tryDirectFacebookLogin(driver, By) {
  const facebookButton = await driver.findElement(
    By.xpath('//button[.//div[contains(text(), "Continue with Facebook")]]'),
  );
  await facebookButton.click();
}

async function tryForgotPasswordFlow(driver, commands, By) {
  const forgotButton = await driver.findElement(
    By.xpath('//div[@role="button"][@aria-label="Forgot password?"]'),
  );
  await forgotButton.click();
  await commands.wait.byTime(5000);

  const loginWithFacebook = await driver.findElement(
    By.xpath('//div[@role="button"][@aria-label="Log in with Facebook"]'),
  );
  await loginWithFacebook.click();
  await commands.wait.byTime(5000);

  await handleContinueAsDialog(driver, By, commands);
}

async function handleContinueAsDialog(driver, By, commands) {
  try {
    const continueAsButton = await driver.findElement(
      By.xpath(
        '//button[contains(@class, "_54k8") and .//span[contains(text(), "Continue as")]]',
      ),
    );
    await continueAsButton.click();
  } catch (continueError) {
    console.log("Could not find Continue as button:", continueError);
  }
}

async function handleBackNavigation(driver, commands) {
  console.log("Error in Instagram flow, attempting Android back action");
  await driver.executeScript(`
    const process = await import('child_process');
    process.execSync('adb shell input keyevent KEYCODE_BACK');
  `);
  await commands.wait.byTime(10000);
}
