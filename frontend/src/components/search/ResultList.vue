<script setup>
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
      page: 0,
      per_page: 10,
      ds_and_item_ids: [],
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("visibility_filters_changed", () => {
      this.update_results()
    })
  },
  watch: {
    page(new_val, old_val) {
      this.update_results()
    },
    per_page(new_val, old_val) {
      this.update_results()
    },
    "appStateStore.search_result_ids"(new_val, old_val) {
      this.update_results()
    },
    "appStateStore.selected_cluster_id"(new_val, old_val) {
      this.update_results()
    },
  },
  methods: {
    update_results() {
      this.ds_and_item_ids = this.appStateStore.get_search_result_ids(this.page, this.per_page)
    }
  },
}
</script>


<template>
  <div>
    {{ page }}
    <button @click="page -= 1" :disabled="page === 0">Previous</button>
    <button @click="page += 1">Next</button>

    <ul v-if="appState.search_result_ids.length !== 0" role="list" class="pt-1">
      <li
        v-for="ds_and_item_id in ds_and_item_ids"
        :key="ds_and_item_id.join('_')"
        class="justify-between pb-3">
        <ResultListItem
          :initial_item="appState.search_result_items[ds_and_item_id[0]][ds_and_item_id[1]]"
          :rendering="appState.datasets[ds_and_item_id[0]].result_list_rendering"
          @mouseenter="appState.highlighted_item_id = ds_and_item_id"
          @mouseleave="appState.highlighted_item_id = null"
          @mousedown="appState.show_document_details(ds_and_item_id)"></ResultListItem>
      </li>
    </ul>
    <div
      v-if="ds_and_item_ids.length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Results Yet</p>
    </div>
  </div>
</template>

<style scoped></style>
