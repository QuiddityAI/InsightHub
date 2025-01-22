<script setup>

import {
  PlusIcon,
  TrashIcon,
  InformationCircleIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';

import CollectionItem from "./CollectionItem.vue"
import CollectionTableCell from "./CollectionTableCell.vue";
import BorderButton from "../widgets/BorderButton.vue";
import BorderlessButton from "../widgets/BorderlessButton.vue";
import EditColumnArea from "../columns/EditColumnArea.vue";

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
  props: ["collection_id", "class_name", "is_positive", "item_size_mode"],
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
    last_retrieval_status() {
      return this.collectionStore.collection.most_recent_search_task?.last_retrieval_status
    },
    retrieved_results() {
      return this.last_retrieval_status.retrieved
    },
    available_results() {
      return this.last_retrieval_status.available
    },
    any_source_is_estimated() {
      return !this.last_retrieval_status.available_is_exact
    },
    more_results_are_available() {
      return this.retrieved_results < this.available_results || this.any_source_is_estimated
    },
    is_last_page() {
      return (collectionStore.first_index + collectionStore.per_page) >= collectionStore.filtered_count
    },
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col items-center" v-if="collection">

    <DataTable :value="collectionStore.collection_items" tableStyle="" scrollable size="small"
      class="min-h-0 overflow-x-auto max-w-full" ref="table">
      <template #empty>
        <div v-if="collectionStore.search_mode"
          class="pl-3 xl:pl-8 py-10 flex flex-col gap-3 items-center text-gray-500">
          {{ collection.ui_settings.hide_checked_items_in_search ? 'No not-already-evaluated items found' : 'No items found' }}
        </div>
        <div v-else
          class="pl-3 xl:pl-8 py-10 flex flex-row justify-center text-gray-500">
          No items yet
        </div>
      </template>
      <Column header="" class="pl-5 xl:pl-10 min-w-[520px]">
        <template #header="slotProps">
          <div v-if="collectionStore.search_mode" class="rounded-md bg-white shadow-sm w-full py-1 px-2 flex flex-row justify-between">
            <div class="w-20"></div>
            <span
              class="text-sm text-center"
              v-tooltip.bottom="{value: 'Only search results are shown. &nbsp Exit search to remove results and show saved items.'}">
              Search Results
              <span class="text-xs text-gray-500">({{ `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''}` }})</span>
              <InformationCircleIcon class="ml-1 h-4 w-4 inline text-blue-500">
              </InformationCircleIcon>
            </span>
            <BorderlessButton @click="collectionStore.approve_relevant_search_results"
              v-tooltip.bottom="{ value: 'Approve all (relevant) search results and leave search mode', showDelay: 400}">
              Approve All
            </BorderlessButton>
          </div>
          <span v-else
            class="text-sm rounded-md bg-white shadow-sm w-full py-1 px-2 text-center">
            {{ collectionStore.entity_name_plural || 'Items' }}
          </span>
        </template>
        <template #body="slotProps">
          <CollectionItem
            :dataset_id="slotProps.data.dataset_id"
            :item_id="slotProps.data.item_id"
            :initial_item="slotProps.data.metadata"
            :is_positive="slotProps.data.is_positive"
            :show_remove_button="true"
            :collection_item="slotProps.data"
            :size_mode="item_size_mode"
            class="min-w-[520px] max-w-[520px]">
          </CollectionItem>

          <div v-if="collectionStore.search_mode && more_results_are_available && is_last_page && slotProps.index == collectionStore.collection_items.length - 1"
            class="my-5 w-full flex flex-row justify-center">
            <BorderButton @click="collectionStore.add_more_items_from_active_task"
              class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
              v-tooltip.top="{ value: `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''} results retrieved`}">
              Show More Results <PlusIcon class="h-4 w-4 inline"></PlusIcon>
            </BorderButton>
          </div>
        </template>
      </Column>
      <Column v-for="(column, index) in collection.columns" :key="column.identifier" :header="false">
        <template #header="slotProps">
          <button class="rounded-md bg-white shadow-sm text-sm hover:text-blue-500 py-1 px-2 w-full"
            @click="event => {selected_column = column; $refs.column_options.toggle(event)}">
            {{ column.name }}
            <span v-if="column.module === 'relevance'" class="ml-2 text-xs text-gray-500">Click to change criteria</span>
          </button>
        </template>
        <template #body="slotProps">
          <CollectionTableCell :item="slotProps.data" :column="column"
            :columns_with_running_processes="collection.columns_with_running_processes"
            :item_size_mode="item_size_mode">
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

    <EditColumnArea ref="column_options" :selected_column="selected_column">
    </EditColumnArea>

  </div>
</template>

<style scoped>
</style>
