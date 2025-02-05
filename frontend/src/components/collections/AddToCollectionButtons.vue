<script setup>

import {
  HandThumbDownIcon,
  NoSymbolIcon,
  ChevronDownIcon,
  BookmarkIcon,
  PlusIcon,
} from "@heroicons/vue/24/outline"

import OverlayPanel from "primevue/overlaypanel"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["multiple_items"],
  emits: ["addToCollection", "removeFromCollection"],
  data() {
    return {
    }
  },
  watch: {
  },
  computed: {
    ...mapStores(useAppStateStore),
    selected_collection_name() {
      if (this.appStateStore.last_used_collection_id === null) {
        return "Select collection"
      }
      let base_name = this.appStateStore.collections.find((e) => e.id == this.appStateStore.last_used_collection_id).name
      if (base_name.length > 20) {
        base_name = `${base_name.slice(0, 20)}...`
      }
      if (this.appStateStore.last_used_collection_class == "_default") {
        return base_name
      } else {
        let class_name = this.appStateStore.last_used_collection_class
        if (class_name.length > 20) {
          class_name = `${class_name.slice(0, 20)}...`
        }
        return `${base_name} (${class_name})`
      }
    },
  },
  mounted() {
    if (this.appStateStore.last_used_collection_id === null) {
      this.appStateStore.last_used_collection_id = this.appStateStore.collections.length ? this.appStateStore.collections[0].id : null
    }
    if (this.appStateStore.last_used_collection_class === null && this.appStateStore.last_used_collection_id !== null) {
      this.select_default_class()
    }
  },
  methods: {
    select_default_class() {
      if (this.appStateStore.last_used_collection_id !== null) {
        const actual_classes = this.appStateStore.collections.find((e) => e.id == this.appStateStore.last_used_collection_id).actual_classes
        this.appStateStore.last_used_collection_class = actual_classes[0].name
      }
    }
  },
}
</script>

<template>
  <div class="flex flex-row h-7">
      <button class="flex flex-row items-center gap-2 border border-gray-300 rounded-l-md px-3 text-sm text-gray-500 hover:text-blue-500 hover:bg-gray-100"
        @click="$emit('addToCollection', appState.last_used_collection_id, appState.last_used_collection_class, true)"
        v-tooltip.bottom="{ value: 'Save this item in a collection', showDelay: 500 }">
        <BookmarkIcon class="h-4 w-4 text-blue-500"></BookmarkIcon> {{ selected_collection_name }}
      </button>
      <button class="border-r border-t border-b border-gray-300 rounded-r-md px-2 py-[3px] text-xs text-gray-500 hover:text-blue-500 hover:bg-gray-100"
        @click="event => {$refs.select_collection_overlay.toggle(event)}"
        v-tooltip.bottom="{ value: 'Select a different collection', showDelay: 300 }">
        <ChevronDownIcon class="h-3 w-3"></ChevronDownIcon>
      </button>

    <OverlayPanel ref="select_collection_overlay">
      <div class="flex flex-row gap-3">
        <select
          v-model="appState.last_used_collection_id"
          @change="select_default_class"
          class="h-8 w-54 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
          <option v-for="collection in appState.collections" :value="collection.id">
            {{ collection.name }}
          </option>
        </select>
        <select
          v-if="appState.last_used_collection_id !== null"
          v-model="appState.last_used_collection_class"
          class="h-8 w-32 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
          <option
            v-for="class_details in appState.collections.find((e) => e.id == appState.last_used_collection_id).actual_classes"
            :value="class_details.name">
            {{ class_details.name == "_default" ? "Items" : class_details.name }}
          </option>
        </select>
        <button
          title="Add to collection"
          @click="
            $emit('addToCollection', appState.last_used_collection_id, appState.last_used_collection_class, true);
            $refs.select_collection_overlay.hide()
          "
          class="mr-1 w-8 rounded-md px-2 text-green-600/50 ring-1 ring-gray-300 hover:bg-green-100">
          <PlusIcon></PlusIcon>
        </button>
        <button
          v-if="appState.dev_mode"
          @click="
            $emit('addToCollection', appState.last_used_collection_id, appState.last_used_collection_class, false);
            $refs.select_collection_overlay.hide()
          "
          class="w-8 rounded-md px-2 text-red-600/50 ring-1 ring-gray-300 hover:bg-red-100">
          <HandThumbDownIcon></HandThumbDownIcon>
        </button>
        <button
          v-if="multiple_items"
          @click="
            $emit('removeFromCollection', appState.last_used_collection_id, appState.last_used_collection_class);
            $refs.select_collection_overlay.hide()
          "
          class="w-8 rounded-md px-2 text-gray-300 ring-1 ring-gray-300 hover:bg-red-100"
          v-tooltip.right="{ value: 'Remove items from collection', showDelay: 300 }">
          <NoSymbolIcon></NoSymbolIcon>
        </button>
      </div>
    </OverlayPanel>
  </div>
</template>

<style scoped></style>
