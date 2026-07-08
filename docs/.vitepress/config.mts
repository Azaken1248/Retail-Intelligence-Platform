import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "Retail Intelligence",
  description: "Enterprise analytical data pipeline, MCP server & AI Agent",
  base: "/",
  cleanUrls: true,
  
  // Light mode by default, support toggling to dark mode
  appearance: true,

  markdown: {
    config: (md) => {
      const fence = md.renderer.rules.fence;
      if (fence) {
        md.renderer.rules.fence = (tokens, idx, options, env, self) => {
          const token = tokens[idx];
          if (token.info.trim() === 'mermaid') {
            return `<div class="mermaid">${token.content}</div>`;
          }
          return fence(tokens, idx, options, env, self);
        };
      }
    }
  },

  themeConfig: {
    logo: {
      light: '/assets/logo-light.svg',
      dark: '/assets/logo-dark.svg',
      alt: 'Retail Intelligence Logo'
    },
    siteTitle: 'Retail Intelligence',

    // Header navigation
    nav: [
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'Architecture', link: '/guide/architecture' },
      { text: 'API & MCP Reference', link: '/guide/api-mcp' },
      {
        text: 'Medallion Layers',
        items: [
          { text: 'Ingestion (Bronze)', link: '/guide/medallion-bronze' },
          { text: 'Refining (Silver)', link: '/guide/medallion-silver' },
          { text: 'Serving (Gold)', link: '/guide/medallion-gold' }
        ]
      }
    ],

    // Sidebar navigation
    sidebar: {
      '/guide/': [
        {
          text: 'Platform Overview',
          collapsed: false,
          items: [
            { text: 'Introduction', link: '/guide/introduction' },
            { text: 'System Architecture', link: '/guide/architecture' }
          ]
        },
        {
          text: 'Medallion Data Pipeline',
          collapsed: false,
          items: [
            { text: 'Bronze Ingestion', link: '/guide/medallion-bronze' },
            { text: 'Silver Processing & Quality', link: '/guide/medallion-silver' },
            { text: 'Gold Serving & Schema', link: '/guide/medallion-gold' }
          ]
        },
        {
          text: 'APIs & Interfaces',
          collapsed: false,
          items: [
            { text: 'REST API Endpoints', link: '/guide/api-rest' },
            { text: 'Model Context Protocol (MCP)', link: '/guide/api-mcp' },
            { text: 'GenAI Agent & Personas', link: '/guide/api-agent' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Azaken1248/Retail-Intelligence-Platform' }
    ],

    footer: {
      message: 'Retail Intelligence Platform Documentation. Built with VitePress.',
      copyright: 'Copyright © 2026'
    }
  }
})
