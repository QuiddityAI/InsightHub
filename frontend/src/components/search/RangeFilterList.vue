<script setup>
import RangeFilterItem from './RangeFilterItem.vue';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      dataset_ids: new Set(),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    range_filters() {
      const filters = {}
      const dataset_ids = new Set()
      // FIXME: this only uses the last search
      const task = this.collectionStore.collection.most_recent_search_task
      if (task && task.dataset_id !== null) {
        dataset_ids.add(task.dataset_id)
      }
      this.dataset_ids = Array.from(dataset_ids)
      for (const dataset_id of dataset_ids) {
        for (const range_filter of this.appStateStore.datasets[dataset_id]?.merged_advanced_options?.range_filters || []) {
          filters[range_filter.field] = range_filter
        }
      }
      return Object.values(filters)
    }
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
  <div v-if="range_filters.length > 0" class="mt-2 flex flex-col gap-2">
    <RangeFilterItem v-for="range_filter in range_filters"
      :range_filter="range_filter" :dataset_ids="dataset_ids" />
  </div>

</template>

<style scoped>
</style>
