import { HeadContent, Scripts, createRootRoute } from '@tanstack/react-router'
import appCss from '@workspace/ui/globals.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: '音乐情绪实验室 · 整体愉悦度与唤醒度' },
      { name: 'description', content: '上传音乐，在本地 CPU 后端观察整体愉悦度与唤醒度。科研演示，无模拟预测。' },
      { name: 'robots', content: 'noindex, nofollow' },
    ],
    links: [{ rel: 'stylesheet', href: appCss }],
  }),
  notFoundComponent: () => <main className="main-content" style={{ paddingTop: 60 }}><h1>页面未找到</h1><p>请求的页面不存在。</p><a href="/">返回音乐情绪实验室</a></main>,
  shellComponent: RootDocument,
})
function RootDocument({ children }: { children: React.ReactNode }) {
  return <html lang="zh-CN" dir="ltr"><head><HeadContent/></head><body>{children}<Scripts/></body></html>
}
