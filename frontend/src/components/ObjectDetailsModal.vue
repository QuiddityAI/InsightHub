
<script>
export default {
  props: ["item", "abstract"],
  emits: ["addToPositives", "addToNegatives", "close"],
  data() {
    return {

    }
  },
}
</script>


<template>
  <div class="flex-initial flex flex-col overflow-hidden min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
    <p class="flex-none text-sm font-medium leading-6 text-gray-900"><div v-html="item.title"></div></p>
    <p class="flex-none mt-1 truncate text-xs leading-5 text-gray-500">{{ item.container_title }}, {{ item.issued_year.toFixed(0) }}</p>
    <p class="flex-none mt-1 truncate text-xs leading-5 text-gray-500">{{ item.most_important_words }}</p>
    <p class="flex-1 overflow-y-auto mt-2 text-xs leading-5 text-gray-700" v-html="abstract"></p>
    <div class="flex-none flex flex-row">
      <button @click="$emit('addToPositives')" class="px-3 py-1 mr-3 bg-green-600/50 hover:bg-blue-600 rounded">Positive</button>
      <button @click="$emit('addToNegatives')" class="px-3 py-1 mr-3 bg-red-600/50 hover:bg-blue-600 rounded">Negative</button>
      <div class="flex-1"></div>
      <button @click="$emit('close')" class="px-3 py-1 bg-blue-600/50 hover:bg-blue-600 rounded">Close</button>
    </div>
  </div>
</template>
