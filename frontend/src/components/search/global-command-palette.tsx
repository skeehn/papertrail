"use client"

import { CommandPalette, useCommandPalette } from './command-palette'

export function GlobalCommandPalette() {
  const { isOpen, close } = useCommandPalette()

  return <CommandPalette isOpen={isOpen} onClose={close} />
}
