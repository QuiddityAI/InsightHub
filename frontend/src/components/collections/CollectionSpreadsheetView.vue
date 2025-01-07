<script setup>

import {
  PlusIcon,
  DocumentIcon,
  Bars3BottomLeftIcon,
  InformationCircleIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';

import BorderButton from "../widgets/BorderButton.vue";
import BorderlessButton from "../widgets/BorderlessButton.vue";
import SpreadsheetCollectionItem from "./spreadsheet/SpreadsheetCollectionItem.vue"
import SpreadsheetCell from "./spreadsheet/SpreadsheetCell.vue";
import EditColumnArea from "../columns/EditColumnArea.vue";

import { CollectionItemSizeMode } from "../../utils/utils.js"

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
      hovered_row: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collection() {
      return this.collectionStore.collection
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
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>

  <div class="w-full flex flex-col overflow-x-auto" v-if="collection">

    <!-- row of all columns (aka the table) -->
    <div class="flex-none w-full flex flex-row justify-start items-start">

      <!-- index column -->
      <div class="flex flex-col justify-start items-center border-r-[1px] border-[rgba(0,0,0,0.07)]">

        <!-- index column header -->
        <div class="h-[32px] flex-none w-[48px] flex flex-row justify-center items-center border-b-[1px] border-t-[1px] border-[rgba(0,0,0,0.07)]">
          <div class="w-3 h-3 rounded-[3px] border-[1.5px] bg-white hover:border-gray-300 hover:bg-gray-100/50 transition-all"></div>
        </div>

        <!-- index column items -->
        <div class="h-[32px] flex-none w-full flex flex-row justify-center items-center border-b-[1px] border-[rgba(0,0,0,0.07)]"
          :class="{
            'bg-gray-100/50': hovered_row === index,
          }"
          @mouseover="hovered_row = index"
          @mouseleave="hovered_row = null"
          v-for="index in Array.from(Array(collectionStore.collection_items.length).keys())" :key="index">

          <span class="text-xs font-normal text-gray-400"> {{ index + 1 }} </span>
        </div>

      </div>

      <!-- item column -->
      <div class="flex flex-col justify-start items-center border-r-[1px] border-[rgba(0,0,0,0.07)]">

        <!-- item column header -->
        <div class="h-[32px] flex-none w-full flex flex-row justify-start items-center px-2 py-1 hover:bg-gray-100/50 border-b-[1px] border-t-[1px] border-[rgba(0,0,0,0.07)]">

          <DocumentIcon class="h-[13px] w-[13px] text-gray-500 mr-2"></DocumentIcon>

          <div v-if="collectionStore.search_mode" class="text-xs font-normal text-gray-600 flex flex-row justify-start">
            <span
              class="flex flex-row justify-start items-center gap-1"
              v-tooltip.bottom="{value: 'Only search results are shown. \n Exit search to remove results and show saved items.'}">
              Search Results
              <span class="text-xs text-gray-500">({{ `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''}` }})</span>
              <InformationCircleIcon class="ml-1 h-4 w-4 inline text-blue-500">
              </InformationCircleIcon>
            </span>
            <BorderlessButton @click="collectionStore.approve_relevant_search_results"
              class="text-xs"
              v-tooltip.bottom="{ value: 'Approve all (relevant) search results and leave search mode', showDelay: 400}">
              Approve All
            </BorderlessButton>
          </div>

          <div v-else
            class="text-xs font-normal text-gray-600">
            Items
          </div>


        </div>

        <!-- item column items -->
        <div class="h-[32px] border-b-[1px] border-[rgba(0,0,0,0.07)]"
          :class="{
            'bg-gray-100/50': hovered_row === index,
          }"
          @mouseover="hovered_row = index"
          @mouseleave="hovered_row = null"
          v-for="(collection_item, index) in collectionStore.collection_items">

          <SpreadsheetCollectionItem
            :dataset_id="collection_item.dataset_id"
            :item_id="collection_item.item_id"
            :initial_item="collection_item.metadata"
            :is_positive="collection_item.is_positive"
            :show_remove_button="true"
            :collection_item="collection_item"
            :size_mode="item_size_mode"
            @remove="collectionStore.remove_item_from_collection([collection_item.dataset_id, collection_item.item_id], collection_id, class_name)"
            :class="{
              'w-[320px]': item_size_mode <= CollectionItemSizeMode.SMALL,
              'w-[520px]': item_size_mode >= CollectionItemSizeMode.MEDIUM,
            }">
          </SpreadsheetCollectionItem>

        </div>
      </div>

      <!-- custom columns -->
      <div v-for="(column, index) in collection.columns" :key="column.identifier"
        class="flex flex-col justify-start items-center border-r-[1px] border-[rgba(0,0,0,0.07)]">

        <!-- custom column header -->
        <button class="h-[32px] flex-none w-full flex flex-row justify-start items-center px-2 py-1 hover:bg-gray-100/50 border-b-[1px] border-t-[1px] border-[rgba(0,0,0,0.07)]"
          @click="event => {selected_column = column; $refs.column_options.toggle(event)}">

          <Bars3BottomLeftIcon class="h-[15px] w-[15px] text-gray-500 mr-2"></Bars3BottomLeftIcon>
          <span class="text-xs font-normal text-gray-600">
            {{ column.name }}
            <span v-if="column.module === 'relevance'" class="ml-2 text-xs text-gray-400">Click to change criteria</span>
          </span>

        </button>

        <div class="h-[32px] w-full border-b-[1px] border-[rgba(0,0,0,0.07)]"
          :class="{
            'bg-gray-100/50': hovered_row === index,
          }"
          @mouseover="hovered_row = index"
          @mouseleave="hovered_row = null"
          v-for="(collection_item, index) in collectionStore.collection_items">

          <SpreadsheetCell
            :item="collection_item" :column="column"
            :columns_with_running_processes="collection.columns_with_running_processes"
            :item_size_mode="item_size_mode">
          </SpreadsheetCell>

        </div>
      </div>


      <!-- last column -->
      <div class="flex-1 flex flex-col justify-start items-center border-r-[1px] border-[rgba(0,0,0,0.07)]">

        <!-- last column header -->
        <div class="h-[32px] flex-none w-full flex flex-row justify-start items-center border-b-[1px] border-t-[1px] border-[rgba(0,0,0,0.07)]">
          <button class="h-full w-[32px] flex flex-row justify-center items-center hover:bg-gray-100/50 border-r-[1px] border-[rgba(0,0,0,0.07)]"
            @click="$emit('add_column')" v-tooltip.bottom="{ value: 'Add Column', showDelay: 400 }">
            <PlusIcon class="h-3 w-3 text-gray-600"></PlusIcon>
          </button>
        </div>

        <!-- last column items -->
        <div class="h-[32px] flex-none w-full flex flex-row justify-center items-center border-b-[1px] border-[rgba(0,0,0,0.07)]"
          :class="{
            'bg-gray-100/50': hovered_row === index,
          }"
          @mouseover="hovered_row = index"
          @mouseleave="hovered_row = null"
          v-for="(collection_item, index) in collectionStore.collection_items" :key="collection_item.item_id">
          <!-- empty -->
        </div>

      </div>

      <EditColumnArea ref="column_options" :selected_column="selected_column">
      </EditColumnArea>

    </div>  <!-- end of row of all columns (aka table) -->

    <!-- show more results button -->
    <div v-if="collectionStore.search_mode && more_results_are_available && is_last_page"
      class="my-5 w-full flex flex-row justify-center">

      <BorderButton @click="collectionStore.add_items_from_active_sources"
        class="py-1 px-2 rounded-md border border-gray-200 text-sm font-semibold hover:bg-blue-100/50"
        v-tooltip.top="{ value: `${retrieved_results} of ${available_results}${any_source_is_estimated ? '+': ''} results retrieved`}">
        Show More Results <PlusIcon class="h-4 w-4 inline"></PlusIcon>
      </BorderButton>
    </div>

  </div>
</template>

<style scoped>
</style>
