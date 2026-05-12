import { App } from 'antd'

/**
 * 在组件中使用 antd message/notification/modal（消费 context）
 * 用法: const { message, notification, modal } = useApp()
 */
export function useApp() {
  return App.useApp()
}
