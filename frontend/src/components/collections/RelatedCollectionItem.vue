<script setup>
import {
  TrashIcon,
 } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import CollectionTableCell from "./CollectionTableCell.vue"

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store";

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection_item"],
  emits: ["refresh_item"],
  data() {
    return {
      collection: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.collection = this.collectionStore.available_collections.find((collection) => collection.id === this.collection_item.collection)
  },
  watch: {
    collection_item(val, oldVal) {
      this.collection = this.collectionStore.available_collections.find((collection) => collection.id === this.collection_item.collection)
    },
  },
  methods: {
    show_table() {
      this.eventBus.emit("show_table", {collection_id: this.collection_item.collection, class_name: this.collection_item.classes[0]})
    },
  },
}
</script>

<template>

  <div v-if="collection" class="rounded-md bg-gray-100 px-3 pt-2 pb-4">
    <div class="flex flex-col gap-3">

      <div class="flex flex-row gap-4">
        <div class="font-semibold text-gray-600 text-sm">
          {{ collection?.name }}
        </div>
        <div class="flex-1"></div>
        <button class="text-sm text-gray-500 hover:text-sky-500"
          @click="show_table">
          Show Collection
        </button>
        <button
          @click.stop="appState.remove_item_from_collection([collection_item.dataset_id, collection_item.item_id], collection_item.collection, collection_item.classes[0])"
          v-tooltip.right="{ value: 'Remove from this collection', showDelay: 400 }"
          class="text-sm text-gray-400 hover:text-red-600">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>
      </div>

      <div v-for="column in collection.columns" class="flex flex-col w-full">
        <div>
          <span class="text-sm text-gray-600"
            v-tooltip.top="{ value: column.expression, showDelay: 400 }">
            {{ column.name }}
          </span>
        </div>
        <CollectionTableCell :item="collection_item" :column="column" class="bg-white border rounded-md"
          :columns_with_running_processes="collection.columns_with_running_processes"
          :hide_execute_button="true">
        </CollectionTableCell>
      </div>
    </div>

  </div>

  <div v-else>
    <div class="rounded-md bg-gray-100 py-2 px-2 flex flex-col">
      <div class="font-semibold text-gray-600 text-sm">
        Loading...
      </div>
    </div>
  </div>

</template>

<style scoped>
</style>
