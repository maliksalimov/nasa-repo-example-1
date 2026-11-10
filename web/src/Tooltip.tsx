import { useCallback, useRef, useState, type ReactNode } from 'react'

interface Tip {
  x: number
  y: number
  flip: boolean
  content: ReactNode
}

/**
 * Shared tooltip for SVG charts. `show` takes the hovered or focused element,
 * so mouse and keyboard users get the same information.
 */
export function useTooltip() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip | null>(null)

  const show = useCallback((target: Element, content: ReactNode) => {
    const container = containerRef.current
    if (!container) return
    const box = target.getBoundingClientRect()
    const frame = container.getBoundingClientRect()
    const x = box.left + box.width / 2 - frame.left
    // Near the right edge, open the tooltip to the left so it stays on screen.
    setTip({ x, y: box.top - frame.top, flip: x > frame.width - 200, content })
  }, [])

  const hide = useCallback(() => setTip(null), [])

  const element = tip ? (
    <div
      className="tip"
      role="status"
      style={{ left: tip.x, top: tip.y }}
      data-flip={tip.flip ? 'left' : undefined}
    >
      {tip.content}
    </div>
  ) : null

  return { containerRef, show, hide, element }
}

/** Props that wire an SVG mark to the tooltip for pointer and keyboard. */
export function tipHandlers(
  show: (target: Element, content: ReactNode) => void,
  hide: () => void,
  content: ReactNode,
) {
  return {
    tabIndex: 0,
    onPointerEnter: (event: React.PointerEvent<SVGElement>) => show(event.currentTarget, content),
    onPointerLeave: hide,
    onFocus: (event: React.FocusEvent<SVGElement>) => show(event.currentTarget, content),
    onBlur: hide,
  }
}
