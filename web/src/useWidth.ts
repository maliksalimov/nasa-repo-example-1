import { useLayoutEffect, useRef, useState } from 'react'

/** Tracks the rendered width of an element so SVG charts can redraw at any size. */
export function useWidth<T extends HTMLElement>(initial = 800) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(initial)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    // Measure once before paint, then follow resizes.
    setWidth(Math.round(element.getBoundingClientRect().width))
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}
