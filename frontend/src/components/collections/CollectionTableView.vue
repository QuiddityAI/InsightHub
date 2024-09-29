<script setup>

import {
  TrashIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Paginator from "primevue/paginator"
import OverlayPanel from 'primevue/overlaypanel';
import Dropdown from 'primevue/dropdown';

import CollectionItem from "./CollectionItem.vue"
import CollectionTableCell from "./CollectionTableCell.vue";

import { FieldType } from "../../utils/utils"
import { httpClient, djangoClient } from "../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection_id", "class_name", "is_positive"],
  expose: [],
  emits: [],
  data() {
    return {
      selected_column: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collection() {
      return this.collectionStore.collection
    },
    available_modules() {
      return this.appStateStore.available_ai_modules.concat(this.appStateStore.additional_column_modules)
    },
  },
  mounted() {
    const that = this
    this.collectionStore.load_collection_items()
    this.eventBus.on("collection_item_added", ({collection_id, class_name, is_positive, created_item}) => {
      if (collection_id === this.collectionStore.collection_id && class_name === this.collectionStore.class_name && is_positive === this.collectionStore.is_positive) {
        that.collectionStore.load_collection_items()
      }
    })
    this.eventBus.on("collection_item_removed", ({collection_id, class_name, collection_item_id}) => {
      if (collection_id === this.collectionStore.collection_id && class_name === this.collectionStore.class_name) {
        const item_index = that.collectionStore.collection_items.findIndex((item) => item.id === collection_item_id)
        if (item_index >= 0) {
          that.collectionStore.collection_items.splice(item_index, 1)
        }
      }
    })
  },
  watch: {
    'collectionStore.first_index'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.order_by_field'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.order_descending'() {
      this.collectionStore.load_collection_items()
    },
    'collectionStore.collection.items_last_changed'(new_value, old_value) {
      if (new_value > this.collectionStore.items_last_updated) {
        this.collectionStore.load_collection_items()
      }
    },
  },
  methods: {
    delete_column(column_id) {
      const that = this
      if (!confirm("Are you sure you want to delete this column and all of the extraction results and notes?")) {
        return
      }
      const body = {
        column_id: column_id,
      }
      httpClient.post(`/org/data_map/delete_collection_column`, body)
      .then(function (response) {
        that.collectionStore.collection.columns = that.collectionStore.collection.columns.filter((column) => column.id !== column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    remove_results(column_id, only_current_page=true, force=false, on_success=null) {
      const that = this
      if (!only_current_page && !force && !confirm("This will remove the column content for all items in the collection. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.collectionStore.class_name,
        offset: only_current_page ? this.collectionStore.first_index : 0,
        limit: only_current_page ? this.collectionStore.per_page : -1,
        order_by: (this.collectionStore.order_descending ? "-" : "") + this.collectionStore.order_by_field,
      }
      httpClient.post(`/org/data_map/remove_collection_class_column_data`, body)
      .then(function (response) {
        if (on_success) {
          on_success()
        }
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    extract_question(column_id, only_current_page=true) {
      const that = this
      if (!only_current_page && !confirm("This will extract the question for all items in the collection. This might be long running and expensive. Are you sure?")) {
        return
      }
      const body = {
        column_id: column_id,
        class_name: this.collectionStore.class_name,
        offset: only_current_page ? this.collectionStore.first_index : 0,
        limit: only_current_page ? this.collectionStore.per_page : -1,
        order_by: (this.collectionStore.order_descending ? "-" : "") + this.collectionStore.order_by_field,
      }
      httpClient.post(`/org/data_map/extract_question_from_collection_class_items`, body)
      .then(function (response) {
        that.collectionStore.collection.columns_with_running_processes = response.data.columns_with_running_processes
        that.get_extraction_results(column_id)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    get_extraction_results(column_id) {
      const that = this
      const column_identifier = this.collection.columns.find((column) => column.id === column_id).identifier
      this.collectionStore.load_collection_items([column_identifier])
      this.collectionStore.update_collection(() => {
        // if (JSON.stringify(response.data.columns) !== JSON.stringify(that.collection.columns)) {
        //   that.collection.columns = response.data.columns
        // }
        // that.collection.columns_with_running_processes = response.data.columns_with_running_processes
        if (this.collection.columns_with_running_processes.includes(column_identifier)) {
          setTimeout(() => {
            this.get_extraction_results(column_id)
          }, 1000)
        }
      })
    },
    human_readable_source_fields(fields) {
      const available_source_fields = this.collectionStore.available_source_fields
      return fields.map((field) => available_source_fields.find((f) => f.identifier === field).name).join(", ")
    },
    human_readable_module_name(module_identifier) {
      return this.available_modules.find((m) => m.identifier === module_identifier)?.name
    },
  },
}
</script>

<template>
  <div class="flex-1 flex flex-col overflow-x-hidden">
    <DataTable :value="collectionStore.collection_items" tableStyle="" scrollable scrollHeight="flex" size="small" class="min-h-0 overflow-x-auto">
      <template #empty>
        <div class="py-10 flex flex-row justify-center text-gray-500">No items yet</div>
      </template>
      <Column header="">
        <template #header="slotProps">
          <span class="text-sm">Item</span>
        </template>
        <template #body="slotProps">
          <CollectionItem
            :dataset_id="slotProps.data.dataset_id"
            :item_id="slotProps.data.item_id"
            :initial_item="slotProps.data.metadata"
            :is_positive="slotProps.data.is_positive"
            :show_remove_button="true"
            @remove="collectionStore.remove_item_from_collection([slotProps.data.dataset_id, slotProps.data.item_id], collection_id, class_name)"
            class="min-w-[350px] max-w-[520px]">
          </CollectionItem>
        </template>
      </Column>
      <Column v-for="column in collection.columns" :header="false">
        <template #header="slotProps">
          <button class="rounded-md bg-gray-100 text-sm hover:bg-blue-100/50 py-1 px-2"
            @click="event => {selected_column = column; $refs.column_options.toggle(event)}">
            {{ column.name }}
          </button>
        </template>
        <template #body="slotProps">
          <CollectionTableCell :item="slotProps.data" :column="column"
            class="max-w-[400px]"
            :columns_with_running_processes="collection.columns_with_running_processes"
            :show_overlay_buttons="false">
          </CollectionTableCell>
        </template>
      </Column>
    </DataTable>

    <div class="flex flex-row items-center justify-center">
      <Paginator v-model:first="collectionStore.first_index" :rows="collectionStore.per_page" :total-records="collectionStore.item_count"
        class="mt-[0px]"></Paginator>
      <Dropdown v-if="!collectionStore.search_mode"
        v-model="collectionStore.order_by_field"
        :options="collectionStore.available_order_by_fields"
        optionLabel="name"
        optionValue="identifier"
        placeholder="Order By..."
        class="w-40 mr-2 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
      <button v-if="!collectionStore.search_mode"
        @click="collectionStore.order_descending = !collectionStore.order_descending"
        v-tooltip="{'value': 'Sort Order', showDelay: 500}"
        class="w-8 h-8 text-sm text-gray-400 rounded bg-white border border-gray-300 hover:bg-gray-100">
        {{ collectionStore.order_descending ? '▼' : '▲' }}
      </button>
    </div>

    <OverlayPanel ref="column_options">
        <div class="w-[400px] flex flex-col gap-2">
          <!-- <h3 class="font-bold">{{ selected_column.name }}</h3> -->
          <div class="flex flex-row">
            <p class="flex-1">{{ selected_column.expression }}</p>
            <button
              @click="delete_column(selected_column.id); $refs.column_options.hide()"
              class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
              <TrashIcon class="h-4 w-4"></TrashIcon>
            </button>
          </div>
          <p class="text-xs text-gray-500">{{ human_readable_source_fields(selected_column.source_fields) }}</p>
          <p class="text-xs text-gray-500">{{ human_readable_module_name(selected_column.module) }}</p>
          <div v-if="selected_column.module && selected_column.module !== 'notes'" class="flex flex-row gap-2">
            <button @click="extract_question(selected_column.id, true); $refs.column_options.hide()"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
              Extract <span class="text-gray-500">(current page)</span></button>
            <button @click="extract_question(selected_column.id, false); $refs.column_options.hide()"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
              Extract <span class="text-gray-500">(all)</span></button>
          </div>

          <div class="flex flex-row gap-2">
            <button @click="remove_results(selected_column.id, true)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
              Remove results<br><span class="text-gray-500">(current page)</span></button>
            <button @click="remove_results(selected_column.id, false)"
              class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
              Remove results<br><span class="text-gray-500">(all)</span></button>
          </div>
        </div>
    </OverlayPanel>
  </div>
</template>

<style scoped>
</style>
