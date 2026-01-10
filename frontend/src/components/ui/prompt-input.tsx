"use client"

import * as React from "react"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface PromptInputProps extends React.HTMLAttributes<HTMLDivElement> {
    value?: string
    onValueChange?: (value: string) => void
    onSubmit?: () => void
    loading?: boolean
}

const PromptInputContext = React.createContext<PromptInputProps>({})

const PromptInput = React.forwardRef<HTMLDivElement, PromptInputProps>(
    ({ children, className, value, onValueChange, onSubmit, loading, ...props }, ref) => {
        return (
            <PromptInputContext.Provider value={{ value, onValueChange, onSubmit, loading }}>
                <div
                    ref={ref}
                    className={cn(
                        "relative flex flex-col rounded-xl transition-colors focus-within:ring-1 focus-within:ring-ring",
                        className
                    )}
                    {...props}
                >
                    {children}
                </div>
            </PromptInputContext.Provider>
        )
    }
)
PromptInput.displayName = "PromptInput"

const PromptInputTextarea = React.forwardRef<
    HTMLTextAreaElement,
    React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
    const { value, onValueChange, onSubmit } = React.useContext(PromptInputContext)
    const textareaRef = React.useRef<HTMLTextAreaElement>(null)

    React.useImperativeHandle(ref, () => textareaRef.current!)

    React.useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto"
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
        }
    }, [value])

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            onSubmit?.()
        }
    }

    return (
        <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onValueChange?.(e.target.value)}
            onKeyDown={handleKeyDown}
            className={cn(
                "min-h-[40px] w-full resize-none border-0 bg-transparent px-4 py-3 shadow-none focus-visible:ring-0",
                className
            )}
            {...props}
        />
    )
})
PromptInputTextarea.displayName = "PromptInputTextarea"

const PromptInputActions = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => {
    return (
        <div
            ref={ref}
            className={cn("flex items-center justify-end p-2", className)}
            {...props}
        >
            {children}
        </div>
    )
})
PromptInputActions.displayName = "PromptInputActions"

export { PromptInput, PromptInputTextarea, PromptInputActions }
