import type { SidebarOptions } from '@vuepress/theme-default'

export const sidebarEn: SidebarOptions = {
  '/': [
    {
        text: 'User Guide',
        collapsible: true,
        children: [
            {
                text: 'Importing',
                link: '/guide/importing'
            },
            {
                text: 'Getting Started',
                link: '/guide/getting-started'
            },
            {
                text: 'Userproxies',
                link: '/guide/userproxies'
            },
            {
                text: 'FAQ',
                link: '/guide/faq'
            }
        ]
    },
    {
        text: 'Server Guide',
        collapsible: true,
        children: [
            {
                text: 'Logging',
                link: '/server-guide/logging'
            },
            {
                text: 'Automod',
                link: '/server-guide/automod'
            }
        ]
    },
    {
        text: 'Third Party Applications',
        collapsible: true,
        children: [
            {
                text: 'Creating Applications',
                link: '/third-party-applications/creating-applications'
            },
            {
                text: 'API Reference',
                link: '/third-party-applications/api-reference'
            },
            {
                text: 'Application Guide',
                link: '/third-party-applications/application-guide'
            },
            {
                text: 'Adding Logging Support',
                link: '/third-party-applications/logging-support'
            }
        ]
    },
    {
        text: 'Information',
        collapsible: true,
        children: [
            {
                text: 'Privacy Policy',
                link: '/privacy-policy',
            },
            {
                text: 'Terms of Service',
                link: '/terms-of-service'
            },
            {
                text: 'Donate',
                link: '/donate'
            }
        ]
    }
  ]
}