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

const appState = useAppStateStore()
const mapState = useMapStateStore()
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
  },
  mounted() {
    this.collection = this.appStateStore.collections.find((collection) => collection.id === this.collection_item.collection)
  },
  watch: {
    collection_item(val, oldVal) {
      this.collection = this.appStateStore.collections.find((collection) => collection.id === this.collection_item.collection)
    },
  },
  methods: {
    show_table() {
      this.eventBus.emit("show_table", {collection_id: this.collection_item.collection, class_name: this.collection_item.classes[0]})
    },
    run_cell(column) {
      const that = this
      const body = {
        column_id: column.id,
        class_name: this.collection_item.classes[0],
        collection_item_id: this.collection_item.id,
      }
      httpClient.post(`/org/data_map/extract_question_from_collection_class_items`, body)
      .then(function (response) {
        that.collection.current_extraction_processes = response.data.current_extraction_processes
        that.get_extraction_results(column)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_extraction_results(column) {
      const that = this
      if (!that.collection.current_extraction_processes.includes(column.identifier)) {
        this.$emit('refresh_item')
      } else {
        setTimeout(() => {
          this.update_collection_extraction_processes(() => {
            this.get_extraction_results(column)
          })
        }, 1000)
      }
    },
    update_collection_extraction_processes(on_success) {
      const that = this
      const body = {
        collection_id: this.collection.id,
      }
      httpClient.post("/org/data_map/get_collection", body).then(function (response) {
        that.collection.current_extraction_processes = response.data.current_extraction_processes

        if (on_success) {
          on_success()
        }
      })
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
          Show Table
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
          :current_extraction_processes="collection.current_extraction_processes"
          :show_overlay_buttons="true"
          @run_cell="run_cell(column)">
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
