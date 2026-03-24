import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  base: "/rv/",
  srcDir: "docs",
  ignoreDeadLinks: [/^\/home\//],

  head: [['link', { rel: 'icon', href: '/favicon.png' }]],

  title: "RV",
  description: "Framework for procedural synthetic dataset generation",
  locales: {
    en: {
      label: 'English',
      lang: 'en',
      link: '/en/',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Tutorial', link: '/en/tutorial/' },
          { text: 'API', link: '/en/api/' }
        ],
        sidebar: {
          '/en/': [
            {
              text: 'Tutorial',
              items: [
                { text: 'Getting Started', link: '/en/tutorial/' },
                { text: 'Feature Overview', link: '/en/tutorial/features' },
                { text: 'Build from Source', link: '/en/tutorial/github' }
              ]
            },
            {
              text: 'Reference',
              items: [
                { text: 'API', link: '/en/api/' }
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
      title: 'RV',
      description: 'Фреймворк для процедурной генерации синтетических датасетов',
      themeConfig: {
        nav: [
          { text: 'Главная', link: '/ru/' },
          { text: 'Туториал', link: '/ru/tutorial/' },
          { text: 'API', link: '/ru/api/' }
        ],
        sidebar: {
          '/ru/': [
            {
              text: 'Туториал',
              items: [
                { text: 'Быстрый старт', link: '/ru/tutorial/' },
                { text: 'Обзор возможностей', link: '/ru/tutorial/features' },
                { text: 'Сборка из исходников', link: '/ru/tutorial/github' }
              ]
            },
            {
              text: 'Справка',
              items: [
                { text: 'API', link: '/ru/api/' }
              ]
            }
          ],
        },
        outline: {
          level: [2, 4],
          label: "На этой странице"
        },
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

    search: {
      provider: "local",
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Rapid-Vision/rv' }
    ],

    footer: {
      copyright: "Rapid Vision LLC"
    }
  }
})
