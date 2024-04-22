export default {
    root: ({ context, props }) => ({
        class: [
            // Position
            'absolute',
            // Spacing
            {
                'px-1.5': context?.right || context?.left || (!context?.right && !context?.left && !context?.top && !context?.bottom),
                'py-1.5': context?.top || context?.bottom
            }
        ]
    }),
    arrow: ({ context, props }) => ({
        class: [
          // Position
          'absolute',
          // Size
          'w-0',
          'h-0',
          // Shape
          'border-transparent',
          'border-solid',
          {
            'border-y-[0.25rem] border-r-[0.25rem] border-l-0 border-r-surface-600': (context == null ? void 0 : context.right) || !(context != null && context.right) && !(context != null && context.left) && !(context != null && context.top) && !(context != null && context.bottom),
            'border-y-[0.25rem] border-l-[0.25rem] border-r-0 border-l-surface-600': context == null ? void 0 : context.left,
            'border-x-[0.25rem] border-t-[0.25rem] border-b-0 border-t-surface-600': context == null ? void 0 : context.top,
            'border-x-[0.25rem] border-b-[0.25rem] border-t-0 border-b-surface-600': context == null ? void 0 : context.bottom
          },
          // Spacing
          {
            '-mt-1 ': (context == null ? void 0 : context.right) || !(context != null && context.right) && !(context != null && context.left) && !(context != null && context.top) && !(context != null && context.bottom),
            '-mt-1': context == null ? void 0 : context.left,
            '-ml-1': (context == null ? void 0 : context.top) || (context == null ? void 0 : context.bottom)
          }
        ]
    }),
    text: {
        class: [
            // Size
            'text-xs leading-none',

            // Spacing
            'p-2',

            // Shape
            'rounded-md',

            // Color
            'text-surface-900 dark:text-surface-0/80',
            'bg-surface-0 dark:bg-surface-900',
            'ring-1 ring-inset ring-surface-200 dark:ring-surface-800 ring-offset-0',

            // Misc
            'whitespace-pre-line',
            'break-words',

            // Style
            'shadow-[0px_5px_20px_0px_rgba(0,0,0,0.15)]'
        ]
    }
};
