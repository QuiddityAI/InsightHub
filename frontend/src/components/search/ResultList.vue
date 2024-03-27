<script setup>
import Paginator from 'primevue/paginator';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
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
    })
    this.eventBus.on("search_results_cleared", () => {
      this.appStateStore.update_visible_result_ids()
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
    <div v-if="appState.visible_result_ids.length !== 0">
      <Paginator v-model:first="first_index" :rows="per_page" :total-records="appState.visible_result_ids.length"
      class="mt-[0px]"></Paginator>
      <div class="flex flex-row justify-center">
        <div v-if="appState.search_result_ids.length && (!appState.search_result_total_matches || appState.search_result_ids.length === appState.search_result_total_matches)" class="text-xs text-gray-400">
          {{ appState.search_result_ids.length.toLocaleString() }} results found
        </div>
        <div v-else-if="appState.search_result_ids.length && appState.search_result_total_matches" class="text-xs text-gray-400">
          First {{ appState.search_result_ids.length.toLocaleString() }} of ~{{  appState.search_result_total_matches.toLocaleString() }} results are included
        </div>
      </div>
      <ul role="list" class="pt-1">
        <li
          v-for="ds_and_item_id in result_ids_for_this_page"
          :key="ds_and_item_id.join('_')"
          class="justify-between pb-3">
          <ResultListItem
            v-if="appState.search_result_items.hasOwnProperty(ds_and_item_id[0]) && appState.search_result_items[ds_and_item_id[0]].hasOwnProperty(ds_and_item_id[1])"
            :initial_item="appState.search_result_items[ds_and_item_id[0]][ds_and_item_id[1]]"
            :rendering="appState.datasets[ds_and_item_id[0]].result_list_rendering"
            @mouseenter="appState.highlighted_item_id = ds_and_item_id"
            @mouseleave="appState.highlighted_item_id = null"
            @mousedown="appState.show_document_details(ds_and_item_id)"></ResultListItem>
        </li>
      </ul>
      <Paginator v-model:first="first_index" :rows="per_page" :total-records="appState.visible_result_ids.length"></Paginator>
    </div>
    <div
      v-if="appState.visible_result_ids.length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Results</p>
    </div>
  </div>
</template>

<style scoped></style>
