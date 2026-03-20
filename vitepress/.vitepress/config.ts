import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  srcDir: "docs",

  head: [['link', { rel: 'icon', href: '/favicon.png' }]],


  title: "RV Framework",
  description: "Framework for procedural synthetic dataset generation",
  locales: {
    root: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: [
          { text: 'Tutorial', link: '/tutorial/' },
          { text: 'API', link: '/api/' }
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
    },
    ru: {
      label: 'Русский',
      lang: 'ru',
      link: '/ru/',
      title: 'RV Framework',
      description: 'Фреймворк для процедурной генерации синтетических датасетов',
      themeConfig: {
        nav: [
          { text: 'Главная', link: '/ru/' },
          { text: 'Туториал', link: '/ru/tutorial/' },
          { text: 'API', link: '/api/' }
        ],
        sidebar: {
          '/ru/': [
            {
              text: 'Туториал',
              items: [
                { text: 'Быстрый старт', link: '/ru/tutorial/' },
                { text: 'Сборка из исходников', link: '/ru/tutorial/github' }
              ]
            },
            {
              text: 'Справка',
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
    }
  },
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    outline: [2, 4],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Rapid-Vision/rv' }
    ],

    footer: {
      copyright: "Rapid Vision LLC"
    }
  }
})
