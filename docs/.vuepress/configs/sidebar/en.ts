import type { SidebarOptions } from '@vuepress/theme-default'

export const sidebarEn: SidebarOptions = {
  '/': [
    {
        text: 'Guide',
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