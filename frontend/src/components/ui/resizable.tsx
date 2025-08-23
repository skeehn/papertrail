"use client"

import * as React from "react"
import { GripVertical } from "lucide-react"

import { cn } from "@/lib/utils"

const RESIZE_HANDLE_SIZE = 4

interface ResizablePanelGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: "horizontal" | "vertical"
}

const ResizablePanelGroup = React.forwardRef<
  HTMLDivElement,
  ResizablePanelGroupProps
>(({ className, direction = "horizontal", ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex h-full w-full",
      direction === "horizontal" ? "flex-row" : "flex-col",
      className
    )}
    {...props}
  />
))
ResizablePanelGroup.displayName = "ResizablePanelGroup"

interface ResizablePanelProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultSize?: number
  minSize?: number
  maxSize?: number
}

const ResizablePanel = React.forwardRef<
  HTMLDivElement,
  ResizablePanelProps
>(({ className, defaultSize, minSize, maxSize, style, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative", className)}
    style={{
      flex: defaultSize ? `0 0 ${defaultSize}%` : "1 1 0%",
      minWidth: minSize ? `${minSize}%` : undefined,
      maxWidth: maxSize ? `${maxSize}%` : undefined,
      ...style,
    }}
    {...props}
  />
))
ResizablePanel.displayName = "ResizablePanel"

const ResizableHandle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative flex w-px items-center justify-center bg-border after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1",
      "hover:bg-gray-300 hover:w-1",
      "cursor-col-resize select-none touch-none transition-colors",
      className
    )}
    {...props}
  >
    <GripVertical className="h-2.5 w-2.5 text-gray-400" />
  </div>
))
ResizableHandle.displayName = "ResizableHandle"

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }