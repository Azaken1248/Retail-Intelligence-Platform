import DefaultTheme from 'vitepress/theme'
import { onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vitepress'
import './custom.css'

export default {
  extends: DefaultTheme,
  setup() {
    const router = useRouter()

    const initMermaid = async () => {
      if (typeof window !== 'undefined') {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({
          startOnLoad: false,
          theme: document.documentElement.classList.contains('dark') ? 'dark' : 'default',
          securityLevel: 'loose',
          fontFamily: 'Inter, system-ui, sans-serif'
        })
        
        // Find all mermaid divs/pre blocks and render them
        const elements = document.querySelectorAll('.mermaid')
        if (elements.length > 0) {
          // Re-evaluate mermaid diagrams dynamically
          await mermaid.run()
        }
      }
    }

    onMounted(() => {
      initMermaid()

      // Watch for dark-mode toggle class change on html element
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.attributeName === 'class') {
            initMermaid()
          }
        })
      })
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class']
      })
    })

    // Re-trigger mermaid on router transitions
    watch(
      () => router.route.path,
      () => {
        nextTick(() => {
          setTimeout(initMermaid, 100)
        })
      }
    )
  }
}
