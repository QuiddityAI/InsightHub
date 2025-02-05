<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  highlighted: Boolean,
  hover_color: {
    type: String,
    default: 'hover:text-blue-500',
  },
  highlight_color: {
    type: String,
    default: 'text-blue-500',
  },
  default_padding: {
    type: Boolean,
    default: true,
  },
  badge: {
    type: Number,
    default: 0,
  },
})
</script>

<template>
  <button
    class="relative flex items-center justify-center gap-1 text-sm font-medium border border-gray-200 rounded-md hover:border-gray-300"
    :class="{
      'text-gray-500': !highlighted,
      [highlight_color]: highlighted,
      [hover_color]: !highlighted,
      'px-2': default_padding,
      }">
    <slot></slot>
    <span
      v-if="badge"
      class="absolute -top-2 -right-2 flex items-center justify-center w-4 h-4 text-[11px] font-bold text-white bg-blue-500 rounded-full"
    >
      {{ badge <= 9 ? badge : '+' }}
    </span>
  </button>
</template>
