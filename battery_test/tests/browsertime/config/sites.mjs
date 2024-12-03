export var URLS = [
  "https://facebook.com/",
  "https://instagram.com/",
  "https://instagram.com/explore/",
  "https://buzzfeed.com",
  "https://cnn.com",
  "https://tmz.com",
  "https://perezhilton.com",
  "https://wikipedia.org/wiki/Student%27s_t-test",
  "https://searchfox.org/mozilla-central/source/toolkit/components/telemetry/Histograms.json",
];

export const SITE_TIMINGS = {
  MIN_TIME_PER_SITE: 150,
  MAX_TIME_PER_SITE: 400,
  MAX_TOTAL_TIME: 1800,
  SPECIAL_SITE_TIMES: {
    "https://instagram.com/accounts/login/": 10,
    "https://instagram.com/explore/": 400,
    "https://facebook.com": 400,
  },
};

export const SCROLL_CONFIG = {
  DELAY_TIME: 500,
  SCROLL_WAIT_TIME: 4000,
  MAX_SCROLL_ATTEMPTS: 10,
};
