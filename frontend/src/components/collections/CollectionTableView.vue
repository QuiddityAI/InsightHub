<script setup>

import {
  PlusIcon,
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
import BorderButton from "../widgets/BorderButton.vue";

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
  emits: ["add_column"],
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
    active_search_sources() {
      return this.collectionStore.collection.search_sources.filter((source) => source.is_active)
    },
    retrieved_results() {
      return Math.max(this.active_search_sources.map((source) => source.retrieved))
    },
    available_results() {
      return Math.max(this.active_search_sources.map((source) => source.available))
    },
    any_source_is_estimated() {
      return this.active_search_sources.some((source) => !source.available_is_exact)
    },
    more_results_are_available() {
      return this.retrieved_results < this.available_results || this.any_source_is_estimated
    },
    is_last_page() {
      return (collectionStore.first_index + collectionStore.per_page) >= collectionStore.filtered_count
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
      // scroll table to top:
      this.$refs.table.$el.querySelector('div').scrollTop = 0
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
  <div class="flex-1 flex flex-col items-center overflow-x-hidden" v-if="collection">

    <DataTable :value="collectionStore.collection_items" tableStyle="" scrollable scrollHeight="flex" size="small"
      class="min-h-0 overflow-x-auto pt-3 xl:pt-6 max-w-full" ref="table">
      <template #empty>
        <div class="pl-3 xl:pl-8 py-10 flex flex-row justify-center text-gray-500">No items yet</div>
      </template>
      <Column header="" class="pl-5 xl:pl-10 min-w-[520px]">
        <template #header="slotProps">
          <span class="text-sm rounded-md bg-white shadow-sm w-full py-1 px-2 text-center">{{ collectionStore.search_mode ? 'Search Results' : 'Items' }}</span>
        </template>
        <template #body="slotProps">
          <div v-if="slotProps.index == 0 && collectionStore.search_mode"
            class="mb-3 text-xs text-gray-500 text-center w-full">
            Only search results are shown. &nbsp Exit search to remove results and show saved items.
          </div>

          <CollectionItem
            :dataset_id="slotProps.data.dataset_id"
            :item_id="slotProps.data.item_id"
            :initial_item="slotProps.data.metadata"
            :is_positive="slotProps.data.is_positive"
            :show_remove_button="true"
            :collection_item="slotProps.data"
            @remove="collectionStore.remove_item_from_collection([slotProps.data.dataset_id, slotProps.data.item_id], collection_id, class_name)"
            class="min-w-[520px] max-w-[520px]">
          </CollectionItem>

          <div v-if="collectionStore.search_mode && more_results_are_available && is_last_page && slotProps.index == collectionStore.collection_items.length - 1"
            class="my-5 w-full flex flex-row justify-center">
            <BorderButton @click="collectionStore.add_items_from_active_sources"
              class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
              v-tooltip.top="{ value: `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''} results retrieved`}">
              Show More Results <PlusIcon class="h-4 w-4 inline"></PlusIcon>
            </BorderButton>
          </div>
        </template>
      </Column>
      <Column v-for="(column, index) in collection.columns" :header="false">
        <template #header="slotProps">
          <button class="rounded-md bg-white shadow-sm text-sm hover:text-blue-500 py-1 px-2 w-full"
            @click="event => {selected_column = column; $refs.column_options.toggle(event)}">
            {{ column.name }}
          </button>
        </template>
        <template #body="slotProps">
          <CollectionTableCell :item="slotProps.data" :column="column"
            :columns_with_running_processes="collection.columns_with_running_processes"
            :show_overlay_buttons="false">
          </CollectionTableCell>
        </template>
      </Column>
      <Column class="pr-5 xl:pr-10">
        <template #header="slotProps">
          <button class="rounded-md bg-gray-100 shadow-sm text-sm hover:text-blue-500 py-1 px-3 w-[120px]"
            @click="$emit('add_column')">
            <PlusIcon class="h-4 w-4 inline"></PlusIcon> Column
          </button>
        </template>
        <template #body="slotProps">

        </template>
      </Column>
    </DataTable>

    <div class="w-full flex flex-row items-center justify-center bg-white border-t">
      <Paginator v-model:first="collectionStore.first_index" :rows="collectionStore.per_page"
        :total-records="collectionStore.filtered_count"
        class="mt-[0px]"></Paginator>
      <Dropdown v-if="!collectionStore.search_mode"
        v-model="collectionStore.order_by_field"
        :options="collectionStore.available_order_by_fields"
        optionLabel="name"
        optionValue="identifier"
        placeholder="Order By..."
        class="w-44 mr-2 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500" />
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
          <button @click="collectionStore.extract_question(selected_column.id, true); $refs.column_options.hide()"
            class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
            Extract <span class="text-gray-500">(current page)</span></button>
          <button @click="collectionStore.extract_question(selected_column.id, false); $refs.column_options.hide()"
            class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-green-800">
            Extract <span class="text-gray-500">(all)</span></button>
        </div>

        <div class="flex flex-row gap-2">
          <button @click="collectionStore.remove_results(selected_column.id, true)"
            class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
            Remove results<br><span class="text-gray-500">(current page)</span></button>
          <button @click="collectionStore.remove_results(selected_column.id, false)"
            class="flex-1 p-1 bg-gray-100 hover:bg-blue-100/50 rounded text-sm text-red-800">
            Remove results<br><span class="text-gray-500">(all)</span></button>
        </div>
      </div>
    </OverlayPanel>

  </div>
</template>

<style scoped>
</style>
