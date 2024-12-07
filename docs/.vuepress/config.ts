import { removeHtmlExtensionPlugin } from 'vuepress-plugin-remove-html-extension'
import { backToTopPlugin } from '@vuepress/plugin-back-to-top'
import { searchPlugin } from '@vuepress/plugin-search'
import { defaultTheme } from '@vuepress/theme-default'
import { viteBundler } from '@vuepress/bundler-vite'
import { shikiPlugin } from '@vuepress/plugin-shiki'
import { gitPlugin } from '@vuepress/plugin-git'
import { defineUserConfig } from 'vuepress'
import {
  head,
  navbarEn,
  sidebarEn,
} from './configs/index.js'

export default defineUserConfig({
  head,
  locales: {
    '/': {
      lang: 'en-US',
      title: '/plu/ral',
    }
  },
  bundler: viteBundler(),
  theme: defaultTheme({
    hostname: 'https://plural.gg',
    logo: '/images/plural.png',
    repo: 'tyrantlink/plural',
    docsDir: 'docs',
    locales: {
      '/': {
        navbar: navbarEn,
        sidebar: sidebarEn,
        editLinkText: 'Edit this page on GitHub',
      },
    }
  }),
  plugins: [
    backToTopPlugin(),
    removeHtmlExtensionPlugin(),
    searchPlugin(),
    gitPlugin(),
    shikiPlugin({
      themes: { light: 'github-light', dark: 'github-dark' },
      langs: ['py', 'json'],
    })]
})