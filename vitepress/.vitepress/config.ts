import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  srcDir: "docs",

  title: "RV Framework",
  description: "Framework for procedural synthetic dataset generation",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Tutorial', link: '/tutorial/' },
      { text: 'API', link: '/api' }
    ],
    sidebar: {
      '/': [
        {
          text: 'Tutorial',
          items: [
            { text: 'Getting Started', link: '/tutorial/' },
            { text: 'Build from Source', link: '/tutorial/github' }
          ]
        },
        {
          text: 'Reference',
          items: [
            { text: 'API', link: '/api/' }
          ]
        }
      ],
    },

    outline: [2, 4],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Rapid-Vision/rv' }
    ],

    footer: {
      copyright: "Rapid Vision LLC"
    }
  }
})
