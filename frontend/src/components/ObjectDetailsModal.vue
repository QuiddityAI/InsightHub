<script setup>
import { HandThumbUpIcon, HandThumbDownIcon, XMarkIcon } from '@heroicons/vue/24/outline';

import httpClient from '../api/httpClient';
</script>

<script>

export default {
  props: ["schema", "initial_item", "collections", "last_used_collection_id"],
  emits: ["addToPositives", "addToNegatives", "showSimilarItems", "close"],
  data() {
    return {
      selected_collection_id: null,
      rendering: null,
      item: this.initial_item,
    }
  },
  methods: {
    updateItemAndRendering() {
      if (!this.item || !this.item._id) return;
      const that = this
      const rendering = this.schema.detail_view_rendering
      for (const field of ['title', 'subtitle', 'body', 'image', 'url']) {
        rendering[field] = eval(rendering[field])
      }
      that.rendering = rendering

      const payload = {
        schema_id: this.schema.id,
        item_id: this.item._id,
        fields: this.schema.detail_view_rendering.required_fields
      }
      httpClient.post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = response.data
        })
    }
  },
  watch: {
    initial_item() {
      this.item = this.initial_item
      this.updateItemAndRendering()
    },
  },
  mounted() {
    this.updateItemAndRendering()
    if (this.last_used_collection_id === null) {
      this.selected_collection_id = this.collections.length ? this.collections[0].id : null
    } else {
      this.selected_collection_id = this.last_used_collection_id
    }
  },
}
</script>


<template>
  <div class="flex-initial flex flex-col overflow-hidden min-w-0 flex-auto rounded-md shadow-sm bg-white p-3">
    <p class="flex-none text-sm font-medium leading-6 text-gray-900"><div v-html="rendering ? rendering.title(item) : ''"></div></p>
    <p class="flex-none mt-1 truncate text-xs leading-5 text-gray-500"><div v-html="rendering ? rendering.subtitle(item) : ''"></div></p>
    <p class="flex-1 overflow-y-auto mt-2 text-xs leading-5 text-gray-700" v-html="(rendering ? rendering.body(item) : '') || 'loading...'"></p>
    <div class="flex-none flex flex-row mt-2">
      <select v-model="selected_collection_id" class="mr-3 ring-1 ring-gray-300 text-gray-500 text-sm border-transparent rounded-md focus:ring-blue-500 focus:border-blue-500">
        <option v-for="collection in collections" :value="collection.id">{{ collection.name }}</option>
      </select>
      <button @click="$emit('addToPositives', selected_collection_id)" class="w-10 px-3 mr-3 text-green-600/50 ring-1 ring-gray-300 hover:bg-green-100 rounded-md">
        <HandThumbUpIcon></HandThumbUpIcon>
      </button>
      <button @click="$emit('addToNegatives', selected_collection_id)" class="w-10 px-3 mr-3 text-red-600/50 ring-1 ring-gray-300 hover:bg-red-100 rounded-md">
        <HandThumbDownIcon></HandThumbDownIcon>
      </button>
      <button @click="$emit('showSimilarItems')" class="px-3 mr-3 text-sm text-gray-500 ring-1 ring-gray-300 hover:bg-blue-100 rounded-md">
        Show Similar Items
      </button>
      <div class="flex-1"></div>
      <button @click="$emit('close')" class="w-12 px-3 text-gray-500 hover:bg-gray-100 rounded-md">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>
  </div>
</template>

<style scoped></style>
