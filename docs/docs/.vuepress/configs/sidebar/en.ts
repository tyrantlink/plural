import type { SidebarOptions } from '@vuepress/theme-default'

export const sidebarEn: SidebarOptions = {
  '/': [
    {
        text: 'User Guide',
        collapsible: true,
        children: [
            {
                text: 'Getting Started',
                link: '/guide/getting-started'
            },
            {
                text: 'Importing',
                link: '/guide/importing'
            },
            {
                text: 'Config',
                link: '/guide/config'
            },
            {
                text: 'Members',
                link: '/guide/members'
            },
            {
                text: 'Groups',
                link: '/guide/groups'
            },
            {
                text: 'Proxying',
                link: '/guide/proxying'
            },
            {
                text: 'Userproxies',
                link: '/guide/userproxies'
            },
            {
                text: 'Multiple Accounts',
                link: '/guide/multiple-accounts'
            },
            {
                text: 'FAQ',
                link: '/guide/faq'
            },
            {
                text: 'Command Reference',
                link: '/guide/command-reference'
            }
        ]
    },
    {
        text: 'Server Guide',
        collapsible: true,
        children: [
            {
                text: 'Config',
                link: '/server-guide/config'
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
            // {
            //     text: 'Creating Applications',
            //     link: '/third-party-applications/creating-applications'
            // },
            {
                text: 'API Reference',
                link: '/third-party-applications/api-reference'
            },
            // {
            //     text: 'Application Guide',
            //     link: '/third-party-applications/application-guide'
            // },
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