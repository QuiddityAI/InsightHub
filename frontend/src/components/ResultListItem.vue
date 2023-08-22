
<script>
export default {
  props: ["item"],
  data() {
    return {

    }
  },
}
</script>

<template>
  <div class="bg-gray-100/50 rounded p-3">
    <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item.title_enriched"></div></p>
    <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
    <p class="mt-1 truncate text-xs leading-5 text-gray-500">{{ item.most_important_words }}</p>
    <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="item.abstract_enriched"></div></p>
  </div>
</template>
