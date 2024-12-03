import path from "path";
console.log("Resolved path:", path.resolve("./config/sites.mjs"));
import { URLS, SITE_TIMINGS, SCROLL_CONFIG } from "./config/sites.mjs";
import { loginToFacebook } from "./utils/facebook-login.mjs";
import { loginToInstagram } from "./utils/instagram-login.mjs";
import { handleScrolling } from "./utils/scroll-handler.mjs";

let instagramLoggedIn = false;

export default async function (context, commands) {
  const { webdriver, driver } = context.selenium;
  const { By, until } = webdriver;
  const startTime = Date.now();

  for (const url of URLS) {
    const siteStartTime = Date.now();
    const allocatedTime =
      SITE_TIMINGS.SPECIAL_SITE_TIMES[url] || SITE_TIMINGS.MIN_TIME_PER_SITE;

    try {
      await navigateAndLogin(url, driver, commands, By, until);
      await handleSiteInteraction(
        url,
        commands,
        siteStartTime,
        allocatedTime,
        startTime,
      );
    } catch (error) {
      console.error(`Error while navigating or scrolling on ${url}:`, error);
    }

    if (isMaxTimeExceeded(startTime)) {
      console.log(`Total time limit reached. Stopping script.`);
      break;
    }
  }

  console.log("Script finished");
}

async function navigateAndLogin(url, driver, commands, By, until) {
  await commands.switch.toNewTab(url);
  console.log(`Switched to new tab for ${url}`);
  await commands.wait.byTime(1000);

  if (url.includes("facebook.com")) {
    console.log("bout to");
    await loginToFacebook(driver, commands, By, until);
  }

  if (url.includes("instagram.com") && !instagramLoggedIn) {
    await loginToInstagram(driver, commands, By);
    instagramLoggedIn = true;
  }
}

async function handleSiteInteraction(
  url,
  commands,
  siteStartTime,
  allocatedTime,
  startTime,
) {
  const minSiteTimeReached = await handleScrolling(
    url,
    commands,
    siteStartTime,
    allocatedTime,
    startTime,
    SITE_TIMINGS.MAX_TOTAL_TIME,
    SITE_TIMINGS.MIN_TIME_PER_SITE,
  );

  await ensureMinimumTime(url, siteStartTime, minSiteTimeReached, commands);
}

async function ensureMinimumTime(
  url,
  siteStartTime,
  minSiteTimeReached,
  commands,
) {
  if (!minSiteTimeReached && !url.includes("instagram.com/accounts/login")) {
    const remainingTime =
      SITE_TIMINGS.MIN_TIME_PER_SITE - (Date.now() - siteStartTime) / 1000;
    if (remainingTime > 0) {
      console.log(
        `Waiting for ${remainingTime} seconds to reach minimum time for ${url}`,
      );
      await commands.wait.byTime(remainingTime * 1000);
    }
  }
}

function isMaxTimeExceeded(startTime) {
  return (Date.now() - startTime) / 1000 > SITE_TIMINGS.MAX_TOTAL_TIME;
}
