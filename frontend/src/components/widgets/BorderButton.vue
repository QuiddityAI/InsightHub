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
})
</script>

<template>
  <button
    class="flex items-center justify-center gap-1 text-sm font-bold border border-gray-200 rounded-md hover:border-gray-300"
    :class="{
      'text-gray-500': !highlighted,
      [highlight_color]: highlighted,
      [hover_color]: !highlighted,
      'px-2': default_padding,
      }">
    <slot></slot>
  </button>
</template>
