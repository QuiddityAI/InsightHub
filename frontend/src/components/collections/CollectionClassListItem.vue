<script setup>
import {
  TrashIcon
} from "@heroicons/vue/24/outline"
</script>

<script>
export default {
  props: ["class_details", "show_trash_button"],
  emits: ["collection_selected", "class_selected", "delete_collection_class"],
  data() {
    return {}
  },
  computed: {},
  mounted() {},
  methods: {},
}
</script>

<template>
  <li class="mb-2 flex flex-row rounded-md bg-white py-[3px] pr-2 hover:bg-blue-500/10">
    <button class="flex flex-1 flex-row">
      <span class="pl-2 text-sm text-gray-500">
        {{ class_details.name == "_default" ? "Items" : class_details.name }}
      </span>
      <div class="flex-1"></div>
      <span
        class="w-9 text-sm text-gray-500"
        :class="{
        'text-green-700': class_details.positive_count > 0,
      }">
        + {{ class_details.positive_count }}
      </span>
      <span
        class="w-9 text-sm text-gray-500"
        :class="{
        'text-red-700': class_details.negative_count > 0,
      }">
        - {{ class_details.negative_count }}
      </span>
      <button v-if="show_trash_button"
        @click.stop="$emit('delete_collection_class', class_details)"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
      <!-- <button
        @click="$emit('recommend_items_for_collection', collection)"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Recommend Similar
      </button>
      <button
        @click="$emit('show_collection_as_map', collection)"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Show Map
      </button> -->
    </button>
  </li>
</template>
