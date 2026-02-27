"use client"

import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container"
import { DotsLoader } from "@/components/prompt-kit/loader"
import {
  Message,
  MessageAction,
  MessageActions,
  MessageContent,
} from "@/components/prompt-kit/message"
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input"
import { Button } from "@/components/ui/button"
import { cn } from "../../lib/utils"
import { useChat, UIMessage } from "@ai-sdk/react"
import {
  AlertTriangle,
  ArrowUp,
  Copy,
  ThumbsDown,
  ThumbsUp,
  RotateCcw,
  Upload,
  FileText,
  Brain,
} from "lucide-react"
import React, { useState, useEffect } from "react"
import { useConversationPersistence } from "@/hooks/use-memory-persistence"
import PaperUpload from "./paper-upload"

type MessageComponentProps = {
  message: UIMessage
  isLastMessage: boolean
}

export const MessageComponent = ({ message, isLastMessage }: MessageComponentProps) => {
    const isAssistant = message.role === "assistant"

    return (
      <Message
        className={cn(
          "mx-auto flex w-full max-w-3xl flex-col gap-2 px-2 md:px-10",
          isAssistant ? "items-start" : "items-end"
        )}
      >
        {isAssistant ? (
          <div className="group flex w-full flex-col gap-0">
            <MessageContent
              className="text-foreground prose w-full min-w-0 flex-1 rounded-lg bg-transparent p-0"
              markdown
            >
              {message.parts
                .map((part) => (part.type === "text" ? part.text : null))
                .join("")}
            </MessageContent>
            <MessageActions
              className={cn(
                "-ml-2.5 flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100",
                isLastMessage && "opacity-100"
              )}
            >
              <MessageAction tooltip="Copy" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <Copy />
                </Button>
              </MessageAction>
              <MessageAction tooltip="Upvote" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <ThumbsUp />
                </Button>
              </MessageAction>
              <MessageAction tooltip="Downvote" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <ThumbsDown />
                </Button>
              </MessageAction>
            </MessageActions>
          </div>
        ) : (
          <div className="group flex w-full flex-col items-end gap-1">
            <MessageContent className="bg-muted text-primary max-w-[85%] rounded-3xl px-5 py-2.5 whitespace-pre-wrap sm:max-w-[75%]">
              {message.parts
                .map((part) => (part.type === "text" ? part.text : null))
                .join("")}
            </MessageContent>
            <MessageActions
              className={cn(
                "flex gap-0 opacity-0 transition-opacity duration-150 group-hover:opacity-100"
              )}
            >
              <MessageAction tooltip="Copy" delayDuration={100}>
                <Button variant="ghost" size="icon" className="rounded-full">
                  <Copy />
                </Button>
              </MessageAction>
            </MessageActions>
          </div>
        )}
      </Message>
    )
  }

const LoadingMessage = () => (
  <Message className="mx-auto flex w-full max-w-3xl flex-col items-start gap-2 px-0 md:px-10">
    <div className="group flex w-full flex-col gap-0">
      <div className="text-foreground prose w-full min-w-0 flex-1 rounded-lg bg-transparent p-0">
        <DotsLoader />
      </div>
    </div>
  </Message>
)

const ErrorMessage = ({ error }: { error: Error }) => (
  <Message className="not-prose mx-auto flex w-full max-w-3xl flex-col items-start gap-2 px-0 md:px-10">
    <div className="group flex w-full flex-col items-start gap-0">
      <div className="text-primary flex min-w-0 flex-1 flex-row items-center gap-2 rounded-lg border-2 border-red-300 bg-red-300/20 px-2 py-1">
        <AlertTriangle size={16} className="text-red-500" />
        <p className="text-red-500">{error.message}</p>
      </div>
    </div>
  </Message>
)

function ScientificChatbot() {
  const [input, setInput] = useState("")
  const [lastSavedMessageCount, setLastSavedMessageCount] = useState(0)
  const [persistenceEnabled, setPersistenceEnabled] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const { saveConversation, loadConversation, clearConversation } = useConversationPersistence()

  const chat = useChat()
  const messages = chat.messages
  const sendMessage = (chat as any).sendMessage as ((msg: { text: string }) => void)
  const status = (chat as any).status as string
  const error = (chat as any).error as Error | undefined
  const setMessages = (chat as any).setMessages as ((msgs: any[]) => void)
  
  // Load persisted conversation on mount
  useEffect(() => {
    const persistedMessages = loadConversation()
    if (persistedMessages.length > 0) {
      setMessages(persistedMessages)
      setLastSavedMessageCount(persistedMessages.length)
    }
    // Enable persistence after initial load
    setTimeout(() => setPersistenceEnabled(true), 1000)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Intentionally run once on mount

  // Save conversation when messages change
  useEffect(() => {
    if (!persistenceEnabled) return

    if (messages.length > 0 && messages.length !== lastSavedMessageCount) {
      setLastSavedMessageCount(messages.length)

      const timeoutId = setTimeout(async () => {
        try {
          await saveConversation(messages)
          console.log('💾 Scientific conversation saved:', messages.length, 'messages')
        } catch (error) {
          console.error('Failed to save conversation:', error)
        }
      }, 1000)

      return () => clearTimeout(timeoutId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, persistenceEnabled, saveConversation])

  const handleSubmit = () => {
    if (!input.trim()) return

    sendMessage({ text: input })
    setInput("")
  }

  const handleClearConversation = () => {
    clearConversation()
    setMessages([])
  }

  const handlePaperUploaded = (paperId: string, metadata: any) => {
    console.log('Paper uploaded:', paperId, metadata)
    setShowUpload(false)
    // Send a message to the chat about the uploaded paper
    sendMessage({ 
      text: `I just uploaded a paper: "${metadata.title}" by ${metadata.authors?.join(', ')}. Can you analyze it for me?` 
    })
  }

  if (showUpload) {
    return (
      <div className="flex h-screen flex-col overflow-hidden">
        <div className="border-b px-4 py-3 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              <h2 className="font-semibold">Upload Research Papers</h2>
            </div>
            <Button
              variant="outline"
              onClick={() => setShowUpload(false)}
              className="flex items-center gap-2"
            >
              <Brain className="w-4 h-4" />
              Back to Chat
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-6">
            <PaperUpload onPaperUploaded={handlePaperUploaded} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <ChatContainerRoot className="relative flex-1 space-y-0 overflow-y-auto">
        <ChatContainerContent className="space-y-12 px-4 py-12">
          {/* Welcome message for empty chat */}
          {messages.length === 0 && (
            <Message className="mx-auto flex w-full max-w-3xl flex-col items-start gap-2 px-0 md:px-10">
              <div className="group flex w-full flex-col gap-0">
                <div className="text-foreground prose w-full min-w-0 flex-1 rounded-lg bg-transparent p-0">
                  <div className="flex items-start gap-3 mb-4">
                    <Brain className="w-6 h-6 text-blue-500 mt-1" />
                    <div>
                      <h3 className="text-lg font-semibold mb-2">Welcome to PaperTrail 2.0!</h3>
                      <p className="text-gray-600 mb-4">
                        I&apos;m your intelligent research assistant. I can help you with scientific literature analysis, 
                        argument mapping, and research insights.
                      </p>
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-gray-700">Try asking me:</p>
                        <ul className="text-sm text-gray-600 space-y-1">
                          <li>• &quot;What papers do I have about machine learning?&quot;</li>
                          <li>• &quot;Find research on neural networks&quot;</li>
                          <li>• &quot;Show me claims about AI accuracy improvements&quot;</li>
                          <li>• &quot;Are there contradictions in my research collection?&quot;</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Message>
          )}

          {messages.map((message, index) => {
            const isLastMessage = index === messages.length - 1

            return (
              <MessageComponent
                key={message.id}
                message={message}
                isLastMessage={isLastMessage}
              />
            )
          })}

          {status === "submitted" && <LoadingMessage />}
          {status === "error" && error && <ErrorMessage error={error} />}
        </ChatContainerContent>
      </ChatContainerRoot>
      
      <div className="inset-x-0 bottom-0 mx-auto w-full max-w-3xl shrink-0 px-3 pb-3 md:px-5 md:pb-5">
        <PromptInput
          isLoading={status !== "ready"}
          value={input}
          onValueChange={setInput}
          onSubmit={handleSubmit}
          className="border-input bg-popover relative z-10 w-full rounded-3xl border p-0 pt-1 shadow-xs"
        >
          <div className="flex flex-col">
            <PromptInputTextarea
              placeholder="Ask about research papers, upload documents, or explore scientific topics..."
              className="min-h-[44px] pt-3 pl-4 text-base leading-[1.3] sm:text-base md:text-base"
            />

            <PromptInputActions className="mt-3 flex w-full items-center justify-between gap-2 p-2">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowUpload(true)}
                  className="text-xs text-muted-foreground flex items-center gap-1"
                >
                  <Upload size={14} />
                  Upload
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleClearConversation}
                  className="text-xs text-muted-foreground"
                  disabled={messages.length === 0}
                >
                  <RotateCcw size={14} />
                  Clear
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="icon"
                  disabled={
                    !input.trim() || (status !== "ready" && status !== "error")
                  }
                  onClick={handleSubmit}
                  className="size-9 rounded-full"
                >
                  {status === "ready" || status === "error" ? (
                    <ArrowUp size={18} />
                  ) : (
                    <span className="size-3 rounded-xs bg-white" />
                  )}
                </Button>
              </div>
            </PromptInputActions>
          </div>
        </PromptInput>
      </div>
    </div>
  )
}

export default ScientificChatbot