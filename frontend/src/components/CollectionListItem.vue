
<script>
export default {
  props: ["item", "isPositive"],
  emits: ["remove"],
  data() {
    return {

    }
  },
}
</script>


<template>
<div class="rounded px-3 py-2" :class="{'bg-green-100/50': isPositive, 'bg-red-100/50': !isPositive}">
  <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item.title"></div></p>
  <p class="truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
  <button @click="$emit('remove')" class="text-sm text-gray-500">Remove</button>
</div>
</template>