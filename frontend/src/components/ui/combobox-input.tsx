import React, { useState, useRef, useEffect, useMemo } from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ComboboxOption {
  value: string;
  label?: string;
}

export interface ComboboxInputProps {
  id?: string;
  value: string | number;
  onChange: (value: string) => void;
  options: (string | ComboboxOption)[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  type?: string;
  title?: string;
  onBlur?: () => void;
}

export const ComboboxInput = React.forwardRef<HTMLInputElement, ComboboxInputProps>(
  (
    {
      id,
      value,
      onChange,
      options,
      placeholder,
      disabled = false,
      className,
      type = "text",
      title,
      onBlur,
    },
    ref
  ) => {
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement | null>(null);

    const normalizedOptions: ComboboxOption[] = useMemo(() => {
      return options.map((opt) =>
        typeof opt === "string" ? { value: opt, label: opt } : opt
      );
    }, [options]);

    // Close on click outside
    useEffect(() => {
      function handleClickOutside(event: MouseEvent) {
        if (
          containerRef.current &&
          !containerRef.current.contains(event.target as Node)
        ) {
          setIsOpen(false);
        }
      }
      if (isOpen) {
        document.addEventListener("mousedown", handleClickOutside);
      }
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }, [isOpen]);

    const strValue = value !== undefined && value !== null ? String(value) : "";

    // Show matching options if typed, or all options if dropdown toggled
    const filteredOptions = useMemo(() => {
      if (!strValue.trim()) return normalizedOptions;
      const lower = strValue.trim().toLowerCase();
      const matched = normalizedOptions.filter(
        (o) =>
          o.value.toLowerCase().includes(lower) ||
          (o.label && o.label.toLowerCase().includes(lower))
      );
      return matched.length > 0 ? matched : normalizedOptions;
    }, [normalizedOptions, strValue]);

    const handleSelectOption = (optValue: string) => {
      onChange(optValue);
      setIsOpen(false);
    };

    return (
      <div ref={containerRef} className="relative w-full">
        <div className="relative flex items-center">
          <input
            id={id}
            ref={(node) => {
              inputRef.current = node;
              if (typeof ref === "function") ref(node);
              else if (ref) (ref as React.MutableRefObject<HTMLInputElement | null>).current = node;
            }}
            type={type}
            value={strValue}
            placeholder={placeholder}
            disabled={disabled}
            title={title}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setIsOpen(true)}
            onBlur={onBlur}
            className={cn(
              "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 pr-8 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
              className
            )}
          />
          <button
            type="button"
            tabIndex={-1}
            disabled={disabled}
            onClick={() => setIsOpen((prev) => !prev)}
            className="absolute right-1 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:text-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50 transition-colors"
            title="Toggle options"
          >
            <ChevronDown className={cn("h-4 w-4 transition-transform duration-200", isOpen && "rotate-180")} />
          </button>
        </div>

        {isOpen && !disabled && normalizedOptions.length > 0 && (
          <div className="absolute left-0 top-full z-50 mt-1 max-h-60 w-full min-w-[160px] overflow-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md animate-in fade-in-80 zoom-in-95">
            {filteredOptions.length === 0 ? (
              <div className="px-2 py-2 text-xs text-muted-foreground text-center">
                No matching options
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value.toLowerCase() === strValue.toLowerCase();
                return (
                  <div
                    key={opt.value}
                    onClick={() => handleSelectOption(opt.value)}
                    className={cn(
                      "flex items-center justify-between rounded-sm px-2.5 py-1.5 text-xs font-medium cursor-pointer transition-colors hover:bg-accent hover:text-accent-foreground select-none",
                      isSelected && "bg-accent/70 font-semibold text-accent-foreground"
                    )}
                  >
                    <span>{opt.label || opt.value}</span>
                    {isSelected && <Check className="h-3.5 w-3.5 text-primary ml-1" />}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    );
  }
);

ComboboxInput.displayName = "ComboboxInput";
