import { defineConfig } from "vitepress";

export default defineConfig({
  base: "/clawforce/",
  ignoreDeadLinks: true,
  appearance: false, // Light theme only, match clawforce-ui
  title: "Clawforce",
  description:
    "Deploy autonomous AI teams that run your work — 24/7, securely, at scale. Infrastructure for persistent, proactive agent workforces.",
  themeConfig: {
    logo: "/clawforce.png",
    nav: [
      { text: "Home", link: "/" },
      { text: "Guide", link: "/guide/quickstart" },
      { text: "Reference", link: "/reference/terminology" },
    ],
    sidebar: {
      "/guide/": [
        {
          text: "Guide",
          items: [
            { text: "Quick Start", link: "/guide/quickstart" },
            { text: "Configuration", link: "/guide/configuration" },
            { text: "Channels", link: "/guide/channels" },
            { text: "Plans", link: "/guide/plans" },
            { text: "Security", link: "/guide/security" },
          ],
        },
      ],
      "/reference/": [
        {
          text: "Reference",
          items: [{ text: "Terminology", link: "/reference/terminology" }],
        },
      ],
    },
    socialLinks: [
      {
        icon: "github",
        link: "https://github.com/saolalab/clawforce",
      },
    ],
  },
});
