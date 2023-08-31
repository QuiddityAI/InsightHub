
<script>
export default {
  props: ["item", "rendering"],
  data() {
    return {

    }
  },
}
</script>

<template>
  <div class="bg-gray-100/50 rounded p-3">
    <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="rendering.title(item)"></div></p>
    <p class="mt-1 truncate text-xs leading-5 text-gray-500"><div v-html="rendering.subtitle(item)"></div></p>
    <p class="mt-2 text-xs leading-5 text-gray-700"><div v-html="rendering.body(item)"></div></p>
    <p class="mt-2 text-xs leading-5 text-gray-700"><a :href="rendering.url(item)">Link</a></p>
    <img class="w-10" :src="rendering.url(item)">
  </div>
</template>
