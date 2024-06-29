<script setup>
import Paginator from 'primevue/paginator';
import Message from 'primevue/message';
import {
  MagnifyingGlassIcon,
} from "@heroicons/vue/24/outline"

import FilterList from "../search/FilterList.vue"
import RangeFilterList from "../search/RangeFilterList.vue"
import StatisticList from "../search/StatisticList.vue"
import SearchQuestionCard from "../search/SearchQuestionCard.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { debounce } from "../../utils/utils"
import ResultListItem from "./ResultListItem.vue";
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
      first_index: 0,
      per_page: 10,
      show_result_search: false,
      apply_text_filter: debounce((event) => {
        this.mapStateStore.modify_text_filter(event.target.value, this.appStateStore)
      }, 500),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    result_ids_for_this_page() {
      return this.appStateStore.visible_result_ids.slice(this.first_index, this.first_index + this.per_page)
    },
  },
  mounted() {
    this.eventBus.on("visibility_filters_changed", () => {
      this.appStateStore.update_visible_result_ids()
      this.first_index = 0
    })
    this.eventBus.on("search_results_cleared", () => {
      this.appStateStore.update_visible_result_ids()
      this.first_index = 0
    })
    this.eventBus.on("show_results_tab", () => {
      this.first_index = 0
    })
  },
  watch: {
    first(new_val, old_val) {
      console.log("first", new_val, old_val)
    },
    "appStateStore.search_result_ids"(new_val, old_val) {
      this.appStateStore.update_visible_result_ids()
    },
    "appStateStore.selected_cluster_id"(new_val, old_val) {
      this.appStateStore.update_visible_result_ids()
    },
  },
  methods: {
  },
}
</script>


<template>
  <div>
    <div v-if="appState.search_result_ids.length !== 0">

      <div class="flex flex-row items-center">
        <div class="flex flex-row justify-center ml-2">
          <div v-if="appState.search_result_ids.length && (!appState.search_result_total_matches || appState.search_result_ids.length >= appState.search_result_total_matches)" class="text-xs text-gray-400">
            {{ appState.search_result_ids.length.toLocaleString() }} results found
            {{ appState.visible_result_ids.length < appState.search_result_ids.length ? `(${appState.visible_result_ids.length.toLocaleString()} after filtering)` : '' }}
          </div>
          <div v-else-if="appState.search_result_ids.length && appState.search_result_total_matches" class="text-xs text-gray-400"
            v-tooltip.right="{ value: 'If there are many total results, only a subset is displayed on the map and in the list', showDelay: 500 }">
            First {{ appState.search_result_ids.length.toLocaleString() }} of ~{{  appState.search_result_total_matches.toLocaleString() }} results<br>
            {{ appState.visible_result_ids.length < appState.search_result_ids.length ? `(${appState.visible_result_ids.length.toLocaleString()} after filtering)` : '' }}
          </div>
        </div>

        <Paginator v-model:first="first_index" :rows="per_page" :total-records="appState.visible_result_ids.length" :pageLinkSize="3"
          class="flex-1 mt-[0px]"></Paginator>

        <button
          v-tooltip.right="{ value: 'Search within results', showDelay: 500 }"
          @click="show_result_search = !show_result_search"
          class="flex-none p-1 rounded hover:bg-gray-100"
          :class="{'bg-blue-100/50': show_result_search}">
          <MagnifyingGlassIcon class="h-5 w-5 text-gray-400"></MagnifyingGlassIcon>
        </button>
      </div>

      <div v-if="show_result_search" class="flex flex-row mb-4 mt-1">
        <input
          v-model="appState.result_search_query"
          @input="event => apply_text_filter(event)"
          class="flex-1 px-2 py-1 border border-gray-200 rounded text-sm text-gray-500"
          placeholder="Search within results (titles only)">
      </div>

      <RangeFilterList></RangeFilterList>

      <FilterList></FilterList>

      <StatisticList></StatisticList>

      <SearchQuestionCard v-if="mapState.map_parameters?.search.question?.length"></SearchQuestionCard>

      <Message v-if="appState.search_result_ids.length && appState.extended_search_results_are_loading" severity="info" :closable="false" class="opacity-70">
        Preview of the results (loading more...)
      </Message>

      <ul role="list" class="mt-3">
        <li
          v-for="(ds_and_item_id, index) in result_ids_for_this_page"
          :key="ds_and_item_id.join('_')"
          class="justify-between pb-3">
          <ResultListItem
            v-if="appState.search_result_items.hasOwnProperty(ds_and_item_id[0]) && appState.search_result_items[ds_and_item_id[0]].hasOwnProperty(ds_and_item_id[1])"
            :initial_item="appState.search_result_items[ds_and_item_id[0]][ds_and_item_id[1]]"
            :rendering="appState.datasets[ds_and_item_id[0]].schema.result_list_rendering"
            :index="index"
            @mouseenter="appState.highlighted_item_id = ds_and_item_id"
            @mouseleave="appState.highlighted_item_id = null"
            @selected="appState.show_document_details(ds_and_item_id)"></ResultListItem>
        </li>
      </ul>
      <Paginator class="mb-3"
        v-model:first="first_index"
        :rows="per_page" :total-records="appState.visible_result_ids.length">
      </Paginator>
    </div>
  </div>
</template>

<style scoped></style>
