var urls = [
  "https://facebook.com/",
  "https://instagram.com/accounts/login/",
  "https://instagram.com",
  "https://instagram.com/explore/",
  "https://buzzfeed.com",
  "https://cnn.com",
  "https://tmz.com",
  "https://perezhilton.com",
  "https://wikipedia.org/wiki/Student%27s_t-test",
  "https://searchfox.org/mozilla-central/source/toolkit/components/telemetry/Histograms.json",
];

const MaxTime = 1800; // 30 minutes in seconds
const MinTimePerSite = 150; // 5 minutes in seconds
const MaxTimePerSite = 400; // 10 minutes in seconds

const specialSites = {
  "https://instagram.com/accounts/login/": 10,
  "https://instagram.com/explore/": 400,
  "https://facebook.com": 400,
  "https://reddit.com/r/all": 400,
  "https://amazon.ca/events/deals": 400,
};

let instagramLoggedIn = false;

export default async function (context, commands) {
  const delayTime = 500;
  const scrollWaitTime = 7000;
  const maxScrollAttempts = 10;
  let startTime = Date.now();

  for (let i = 0; i < urls.length; i++) {
    let url = urls[i];
    let siteStartTime = Date.now();
    let allocatedTime = specialSites[url] || MinTimePerSite;
    let minSiteTimeReached = false;

    console.log(`Navigating to ${url}.`);

    try {
      await commands.switch.toNewTab(url);
      console.log(`Switched to new tab for ${url}`);
      await commands.wait.byTime(1000); // Wait for initial page load
      console.log(`Waited on ${url}`);

      // Login to Facebook
      if (url.includes("facebook.com")) {
        console.log(`Logging into Facebook.`);
        await commands.js.run(`
          document.querySelector('[name="email"]').value = 'EMAIL';
          document.querySelector('[name="pass"]').value = 'PASSWORD';
          document.querySelector('[name="login"]').click();
        `);
        await commands.wait.byTime(5000);
        console.log(`Clicked login button on Facebook.`);

        await commands.js.run(`
          const okButton = Array.from(document.querySelectorAll('button'))
            .find(button => button.textContent.trim() === 'OK');
          if (okButton) {
            okButton.click();
          }
        `);
        await commands.wait.byTime(5000);
        console.log(`Clicked "OK" button after logging into Facebook.`);
      }

      // Login to Instagram once
      if (url.includes("instagram.com") && !instagramLoggedIn) {
        // console.log(`Logging into Instagram.`);

        // // Check if "Switch accounts" button is present and click it
        // const switchAccounts = await commands.js.run(`
        //   // Find the button with text containing "Continue as"
        //   var continueAsButton = Array.from(document.querySelectorAll('button')).find(button => button.textContent.includes("Continue as"));

        //   // Click the button if found
        //   if (continueAsButton) {
        //     continueAsButton.click();
        //   } else {
        //     console.log("Button not found");
        //   }
        // `);
        await commands.addText.byXpath(
          "EMAIL",
          "//input[@aria-label='Phone number, username, or email']",
        );
        await commands.addText.byXpath("PASSWORD", "//input[@type='password']");
        await commands.click.byXpathAndWait(
          "//button[.//div[text()='Log in']]",
        );
        await commands.wait.byTime(10000); // Wait for login to complete
        instagramLoggedIn = true;
        console.log(`Logged into Instagram.`);
      }

      let lastScrollHeight = 0;
      let newScrollHeight = 0;

      for (let attempt = 0; attempt < maxScrollAttempts; attempt++) {
        if (
          (Date.now() - siteStartTime) / 1000 >= allocatedTime ||
          (Date.now() - startTime) / 1000 >= MaxTime
        ) {
          console.log(`Time limit reached for ${url}, moving to next site.`);
          break; // Time limit reached, move to next site
        }

        try {
          console.log(`Scrolling attempt ${attempt + 1} on ${url}.`);

          lastScrollHeight = await commands.js.run(
            "return document.body.scrollHeight",
          );
          console.log(`Initial scroll height: ${lastScrollHeight}`);

          await commands.scroll.toBottom(delayTime);
          console.log(`Scrolled to bottom on ${url}`);
          await commands.wait.byTime(scrollWaitTime); // Wait to allow new content to load
          console.log(
            `Waited for ${scrollWaitTime / 1000} seconds after scrolling on ${url}`,
          );

          newScrollHeight = await commands.js.run(
            "return document.body.scrollHeight",
          );
          console.log(`New scroll height: ${newScrollHeight}`);

          if (newScrollHeight === lastScrollHeight) {
            console.log(
              `No more content to load on ${url}, checking minimum site time.`,
            );
            if ((Date.now() - siteStartTime) / 1000 >= MinTimePerSite) {
              minSiteTimeReached = true;
              break; // Minimum site time reached, move to next site
            } else {
              console.log(`Minimum time not reached for ${url}, waiting...`);
              await commands.wait.byTime(
                (MinTimePerSite - (Date.now() - siteStartTime) / 1000) * 1000,
              );
              minSiteTimeReached = true;
              break;
            }
          }
        } catch (scrollError) {
          console.error(`Error during scrolling on ${url}:`, scrollError);
          break;
        }
      }

      if (!minSiteTimeReached && !url.includes("instagam.com/accounts/login")) {
        const remainingTime =
          MinTimePerSite - (Date.now() - siteStartTime) / 1000;
        if (remainingTime > 0) {
          console.log(
            `Waiting for ${remainingTime} seconds to reach minimum time for ${url}`,
          );
          await commands.wait.byTime(remainingTime * 1000);
        }
      }
    } catch (error) {
      console.error(`Error while navigating or scrolling on ${url}:`, error);
    }

    if ((Date.now() - startTime) / 1000 > MaxTime) {
      console.log(`Total time limit reached. Stopping script.`);
      break;
    }
  }

  console.log("Script finished");
}
