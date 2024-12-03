import { SCROLL_CONFIG } from "../config/sites.mjs";

// utils/scroll-handler.js
// utils/scroll-handler.js
// utils/scroll-handler.js
// utils/scroll-handler.js

// Function to check if we've exceeded time limits for the current page or total session
function isTimeLimitReached(siteStartTime, allocatedTime, startTime, MaxTime) {
  const siteTimeElapsed = (Date.now() - siteStartTime) / 1000;
  const totalTimeElapsed = (Date.now() - startTime) / 1000;
  return siteTimeElapsed >= allocatedTime || totalTimeElapsed >= MaxTime;
}

export async function handleScrolling(
  url,
  commands,
  siteStartTime,
  allocatedTime,
  startTime,
  MaxTime,
  MinTimePerSite,
) {
  let minSiteTimeReached = false;
  let stuckCount = 0;
  const MAX_STUCK_COUNT = 5;

  for (
    let attempt = 0;
    attempt < SCROLL_CONFIG.MAX_SCROLL_ATTEMPTS;
    attempt++
  ) {
    if (isTimeLimitReached(siteStartTime, allocatedTime, startTime, MaxTime)) {
      console.log(`Time limit reached for ${url}, moving to next site.`);
      break;
    }

    try {
      console.log(`Scrolling attempt ${attempt + 1} on ${url}.`);

      const beforeScroll = await commands.js.run(`
        return {
          height: document.documentElement.scrollHeight,
          position: window.pageYOffset,
          viewport: window.innerHeight
        }
      `);

      console.log("Before scroll metrics:", beforeScroll);

      await commands.js.run(`
        function smoothScroll() {
          return new Promise((resolve) => {
            const distance = window.innerHeight;
            const duration = 500;
            const startPos = window.pageYOffset;
            const startTime = performance.now();

            function scroll(currentTime) {
              const elapsed = currentTime - startTime;
              const progress = Math.min(elapsed / duration, 1);

              window.scrollTo(0, startPos + (distance * progress));

              if (progress < 1) {
                requestAnimationFrame(scroll);
              } else {
                resolve();
              }
            }

            requestAnimationFrame(scroll);
          });
        }

        smoothScroll();
      `);

      await commands.wait.byTime(SCROLL_CONFIG.SCROLL_WAIT_TIME);

      const afterScroll = await commands.js.run(`
        return {
          height: document.documentElement.scrollHeight,
          position: window.pageYOffset,
          viewport: window.innerHeight
        }
      `);

      console.log("After scroll metrics:", afterScroll);

      const heightDiff = afterScroll.height - beforeScroll.height;
      const scrollDiff = afterScroll.position - beforeScroll.position;

      if (heightDiff < 100 && scrollDiff < beforeScroll.viewport * 0.5) {
        stuckCount++;
        console.log(
          `Limited progress detected. Attempt ${stuckCount} of ${MAX_STUCK_COUNT}`,
        );

        if (stuckCount >= MAX_STUCK_COUNT) {
          console.log("Maximum stuck attempts reached, checking minimum time");
          if (await hasMetMinTime(siteStartTime, MinTimePerSite, commands)) {
            minSiteTimeReached = true;
            break;
          }
        }
      } else {
        stuckCount = 0;
        console.log("Made good progress, continuing scroll");
      }

      const pauseTime = Math.random() * 1000 + 500;
      await commands.wait.byTime(pauseTime);
    } catch (scrollError) {
      console.error(`Error during scrolling on ${url}:`, scrollError);
      if (await hasMetMinTime(siteStartTime, MinTimePerSite, commands)) {
        minSiteTimeReached = true;
        break;
      }
    }
  }

  return minSiteTimeReached;
}

async function getScrollHeight(commands) {
  return await commands.js.run("return document.body.scrollHeight");
}

async function performScroll(commands) {
  await commands.scroll.toBottom(SCROLL_CONFIG.DELAY_TIME);
}

async function waitForContent(commands) {
  await commands.wait.byTime(SCROLL_CONFIG.SCROLL_WAIT_TIME);
}

async function hasMetMinTime(siteStartTime, MinTimePerSite, commands) {
  const timeElapsed = (Date.now() - siteStartTime) / 1000;
  if (timeElapsed >= MinTimePerSite) {
    return true;
  } else {
    console.log(`Minimum time not reached, waiting...`);
    await commands.wait.byTime((MinTimePerSite - timeElapsed) * 1000);
    return true;
  }
}
